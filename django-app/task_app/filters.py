import shlex
from datetime import date
from django import forms
from django.db.models import Q


# q（キーワード）で横断検索するフィールド。追加するだけで検索対象が増える。
TASK_SEARCH_FIELDS = [
    'title',
    'description',
    'progress_summary',
]

# ORM lookup名 → 文字列値を Python 型に変換する関数。
# フィールドを追加するだけで新しいフィルタが有効になる。
TASK_FILTER_FIELDS = {
    'status__is_done': lambda v: v.lower() not in ('false', '0', 'no'),
    'assignee': int,
    'project': int,
    'status': int,
    'deadline__lte': date.fromisoformat,
    'deadline__gte': date.fromisoformat,
    'tags__name': str,
}


class TaskFilterForm(forms.Form):
    search = forms.CharField(
        required=False,
        label='検索',
        widget=forms.TextInput(attrs={
            'placeholder': 'q=テスト status__is_done=False assignee=me tag=バグ',
            'class': 'form-control',
            'style': 'width: 480px;',
        }),
    )


def parse_search_query(raw, user=None):
    """
    テキスト入力を ORM フィルタ用 dict に変換する。

    書式例: "バグ修正 status__is_done=False assignee=me deadline__lte=2026-06-30"
      - key=value 形式 → TASK_FILTER_FIELDS で許可された ORM lookup として扱う
      - それ以外のトークン → キーワード検索 (q) として扱う
      - assignee=me → ログイン中ユーザの PK に解決する
    """
    q_tokens = []
    filter_parts = {}

    try:
        tokens = shlex.split(raw)
    except ValueError:
        tokens = raw.split()

    for token in tokens:
        if '=' in token:
            key, _, value = token.partition('=')
            if key == 'q':
                # q=テスト 形式でキーワードを明示指定できる
                q_tokens.append(value)
            elif key == 'tag':
                # tag=バグ は tags__name=バグ の短縮形
                filter_parts['tags__name'] = value
            elif key not in TASK_FILTER_FIELDS:
                continue
            elif key == 'assignee' and value == 'me':
                if user is not None:
                    filter_parts[key] = str(user.pk)
            else:
                filter_parts[key] = value
        else:
            q_tokens.append(token)

    result = {}
    if q_tokens:
        result['q'] = ' '.join(q_tokens)
    result.update(filter_parts)
    return result


def apply_task_filters(queryset, parsed):
    """
    parse_search_query の結果を受け取り queryset にフィルタを適用する。

    - q: TASK_SEARCH_FIELDS を icontains で横断検索
    - その他: TASK_FILTER_FIELDS の変換関数で型変換してから filter() に渡す
    新しいフィルタは TASK_FILTER_FIELDS への追加だけで対応できる。
    """
    if q := parsed.get('q', '').strip():
        search_q = Q()
        for field in TASK_SEARCH_FIELDS:
            search_q |= Q(**{f'{field}__icontains': q})
        queryset = queryset.filter(search_q)

    filter_kwargs = {}
    for k, v in parsed.items():
        if k == 'q' or k not in TASK_FILTER_FIELDS:
            continue
        try:
            filter_kwargs[k] = TASK_FILTER_FIELDS[k](v)
        except (ValueError, TypeError):
            pass

    if filter_kwargs:
        queryset = queryset.filter(**filter_kwargs)

    return queryset


class TaskFilterMixin:
    """
    複数ビューでタスクフィルタリングを共通化するミックスイン。
    TASK_FILTER_DEFAULT をサブクラスで上書きしてデフォルト検索を変える。
    セクションごとに異なる param_name と default を渡して複数フィルタに対応できる。
    """
    TASK_FILTER_DEFAULT = ''

    def get_filter_raw(self, param='search', default=None):
        """指定 GET パラメータの生文字列を返す。未指定時は default を使う。"""
        if default is None:
            default = self.TASK_FILTER_DEFAULT
        return self.request.GET.get(param, default)

    def get_parsed_filters(self, param='search', default=None):
        """生のフィルタ文字列を ORM lookup dict に変換して返す。"""
        raw = self.get_filter_raw(param, default)
        return parse_search_query(raw, user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        raw = self.get_filter_raw()
        context['filter_form'] = TaskFilterForm(data={'search': raw})
        context['filter_value'] = raw
        return context
