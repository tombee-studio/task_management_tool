# テストケース一覧

合計 **247 件** のテストケース（task_app: 203 件 / event_app: 44 件）

**最終パス確認: 2026-05-31 JST** — `Ran 247 tests in 47.945s` → **OK**

凡例: ✅ 正常系 ／ ❌ 異常系・境界値 ／ 🐛 既知バグの文書化

---

## task_app

### モデル層

#### ProjectModelTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 1 | `test_str` | `__str__` が name を返す | ✅ |
| 2 | `test_participants_m2m` | participants M2M にユーザーを追加できる | ✅ |

#### StatusModelTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 3 | `test_str` | `__str__` が name を返す | ✅ |
| 4 | `test_is_done_default_false` | `is_done` のデフォルト値が False | ✅ |
| 5 | `test_is_done_can_be_set_true` | `is_done=True` を設定できる | ✅ |

#### TaskModelTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 6 | `test_str` | `__str__` が title を返す | ✅ |
| 7 | `test_parent_relationship` | parent FK が正しく設定される | ✅ |
| 8 | `test_total_subtask_count_zero` | サブタスクなしで `total_subtask_count = 0` | ✅ |
| 9 | `test_total_subtask_count_nonzero` | サブタスク 2 件で `total_subtask_count = 2` | ✅ |
| 10 | `test_completed_subtask_count` | 完了 1 件・未完了 1 件で `completed_subtask_count = 1` | ✅ |
| 11 | `test_completed_subtask_count_all_done` | 全サブタスク完了で `completed_subtask_count = 2` | ✅ |
| 12 | `test_related_tasks_symmetrical` | `related_tasks` の対称性（A→B で B にも A が入る） | ✅ |
| 13 | `test_deadline_optional` | `deadline` がデフォルト NULL | ✅ |
| 14 | `test_completed_at_optional` | `completed_at` がデフォルト NULL | ✅ |

#### TaskDeadlinePropertyTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 15 | `test_days_remaining_no_deadline_returns_none` | deadline なしで `deadline_days_remaining` が None | ❌ |
| 16 | `test_days_remaining_future` | 将来の deadline で正の残日数が返る | ✅ |
| 17 | `test_days_remaining_today` | 当日締切で残日数 0 | ❌ |
| 18 | `test_days_remaining_past` | 過去の deadline で負の残日数が返る | ❌ |
| 19 | `test_urgent_today` | 当日締切は urgent | ❌ |
| 20 | `test_urgent_tomorrow` | 翌日締切は urgent | ❌ |
| 21 | `test_urgent_past_deadline` | 期限超過は urgent | ❌ |
| 22 | `test_urgent_two_days_away_is_false` | 2 日後締切は urgent でない | ❌ |
| 23 | `test_urgent_no_deadline_is_false` | deadline なしは urgent でない | ❌ |
| 24 | `test_urgent_done_task_is_false` | 完了タスクは urgent でない | ❌ |
| 25 | `test_warning_two_days_away` | 2 日後締切は warning | ❌ |
| 26 | `test_warning_three_days_away` | 3 日後締切は warning | ❌ |
| 27 | `test_warning_one_day_away_is_false` | 1 日後締切は warning でない | ❌ |
| 28 | `test_warning_four_days_away_is_false` | 4 日後締切は warning でない | ❌ |
| 29 | `test_warning_no_deadline_is_false` | deadline なしは warning でない | ❌ |
| 30 | `test_warning_done_task_is_false` | 完了タスクは warning でない | ❌ |
| 31 | `test_warning_past_deadline_is_false` | 期限超過は warning でない | ❌ |

#### TaskEventRelationModelTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 32 | `test_event_is_optional` | `event` FK がデフォルト NULL | ✅ |
| 33 | `test_event_link` | `event` FK に Event を紐づけできる | ✅ |
| 34 | `test_event_reverse_accessor_returns_linked_task` | Event の `tasks` 逆参照に紐づけたタスクが含まれる | ✅ |
| 35 | `test_event_reverse_accessor_excludes_unlinked_task` | 紐づけていないタスクは逆参照に含まれない | ❌ |
| 36 | `test_event_delete_nullifies_task_event` | Event 削除でタスクの `event` が NULL になる | ✅ |

#### RuleModelTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 37 | `test_str` | `__str__` が "プロジェクト名: ルール名" を返す | ✅ |
| 38 | `test_enabled_default_true` | `enabled` のデフォルト値が True | ✅ |

#### StatusProjectModelTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 39 | `test_status_can_be_linked_to_project` | Status に project FK を設定できる | ✅ |
| 40 | `test_status_project_is_optional` | project FK は NULL 許容（既存データ互換） | ✅ |
| 41 | `test_project_statuses_accessor` | `project.statuses` 逆参照が機能する | ✅ |
| 42 | `test_project_statuses_excludes_other_project` | 別プロジェクトのステータスは逆参照に含まれない | ❌ |
| 43 | `test_project_statuses_active_filter` | `project.statuses.filter(is_done=False)` で進行中のみ取得できる | ✅ |
| 44 | `test_deleting_project_cascades_to_statuses` | Project 削除で紐づく Status も CASCADE 削除される | ✅ |

---

### DSL 層

#### DSLParseTest（`parse_dsl`）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 45 | `test_single_link` | 1 行の LINK コマンドをパースできる | ✅ |
| 46 | `test_multiple_links` | 複数行の LINK を全てパースできる | ✅ |
| 47 | `test_empty_text` | 空文字列で空リストを返す | ❌ |
| 48 | `test_no_link_command` | LINK を含まない行は無視される | ❌ |
| 49 | `test_case_insensitive` | 小文字の `link` も認識する | ❌ |
| 50 | `test_extra_whitespace_between_tokens` | トークン間の余分な空白を許容する | ❌ |
| 51 | `test_non_link_lines_are_ignored` | LINK 以外の行は無視される | ❌ |
| 52 | `test_returns_correct_ids` | AST に src_id / dst_id が正しく格納される | ✅ |

#### DSLGrammarTest（LARK 文法 — パースのみ）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 53 | `test_tag_bare_name` | TAG に裸の識別子を渡すとパースできる | ✅ |
| 54 | `test_tag_quoted_string` | TAG にクォート文字列（スペース含む）を渡すとパースできる | ✅ |
| 55 | `test_tag_case_insensitive` | 小文字の `tag` も認識する | ❌ |
| 56 | `test_parent_basic` | PARENT コマンドを `->` 記法でパースできる | ✅ |
| 57 | `test_parent_case_insensitive` | 小文字の `parent` も認識する | ❌ |
| 58 | `test_assign_bare_username` | ASSIGN に裸のユーザー名を渡すとパースできる | ✅ |
| 59 | `test_assign_quoted_username` | ASSIGN にクォート文字列（スペース含む）を渡すとパースできる | ✅ |
| 60 | `test_assign_case_insensitive` | 小文字の `assign` / `to` も認識する | ❌ |
| 61 | `test_mixed_commands_in_one_dsl` | LINK・TAG・PARENT・ASSIGN を 1 DSL に混在させてパースできる | ✅ |
| 62 | `test_unknown_commands_ignored_mixed` | 未知行を含む DSL でも既知コマンドのみがパースされる | ❌ |

#### DSLExecuteTest（`execute_dsl` / `execute_link`）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 63 | `test_creates_relation` | LINK 実行で `related_tasks` に関係が追加される | ✅ |
| 64 | `test_nonexistent_task_does_not_raise` | 存在しない Task ID でも例外が発生しない | ❌ |
| 65 | `test_idempotent` | 同じ LINK を 2 回実行しても重複しない | ❌ |
| 66 | `test_execute_link_directly` | `execute_link` を直接呼んでも関係が作成される | ✅ |
| 67 | `test_execute_link_nonexistent_src_does_not_raise` | src が存在しなくても例外が発生しない | ❌ |
| 68 | `test_execute_link_nonexistent_dst_does_not_raise` | dst が存在しなくても例外が発生しない | ❌ |
| 69 | `test_execute_link_both_nonexistent_does_not_raise` | src・dst 両方存在しなくても例外が発生しない | ❌ |
| 70 | `test_multiple_links_in_one_dsl` | 1 DSL に複数 LINK を含む場合に全て実行される | ✅ |

#### DSLExecuteAssignTest（`execute_dsl` / `execute_assign`）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 71 | `test_assign_changes_assignee` | ASSIGN 実行でタスクの担当者が変更される | ✅ |
| 72 | `test_assign_quoted_username` | クォートされたユーザー名でも担当者を変更できる | ✅ |
| 73 | `test_assign_nonexistent_task_does_not_raise` | 存在しない Task ID でも例外が発生しない | ❌ |
| 74 | `test_assign_nonexistent_user_does_not_raise` | 存在しないユーザー名でも例外が発生せず担当者は変わらない | ❌ |
| 75 | `test_execute_assign_directly` | `execute_assign` を直接呼んでも担当者が変更される | ✅ |

#### DSLEventParseTest（EVENT コマンド — パース）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 76 | `test_event_parsed` | `EVENT <task_id> <event_id>` をパースできる | ✅ |
| 77 | `test_event_case_insensitive` | 小文字の `event` も認識する | ❌ |
| 78 | `test_event_mixed_with_other_commands` | LINK と混在する DSL で両コマンドがパースされる | ✅ |
| 79 | `test_non_event_line_ignored` | EVENT を含まない行は無視される | ❌ |

#### DSLExecuteEventTest（EVENT コマンド — 実行）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 80 | `test_execute_event_links_task_to_event` | `execute_event` でタスクに Event が紐づく | ✅ |
| 81 | `test_execute_event_nonexistent_event_does_not_raise` | 存在しない Event ID でも例外が発生しない | ❌ |
| 82 | `test_execute_event_nonexistent_task_does_not_raise` | 存在しない Task ID でも例外が発生しない | ❌ |
| 83 | `test_execute_dsl_event_links_task` | DSL 経由で EVENT を実行してもタスクに Event が紐づく | ✅ |

---

### ルール処理層

#### RulesProcessTest（`process_task_rules`）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 84 | `test_no_rules_no_effect` | ルールがなければ related_tasks は変化しない | ✅ |
| 85 | `test_pattern_no_match_no_dsl` | パターン不一致ではDSLが実行されない | ❌ |
| 86 | `test_disabled_rule_is_ignored` | `enabled=False` のルールは無視される | ❌ |
| 87 | `test_enabled_rule_with_match_links_tasks` | パターン一致でDSLが実行されタスクが繋がる | ✅ |
| 88 | `test_uses_task_description_when_no_text_given` | `text` 省略時はタスクの description を使用する | ✅ |
| 89 | `test_text_param_overrides_description` | `text` 引数が description より優先される | ✅ |
| 90 | `test_task_id_is_substituted_in_template` | `{task_id}` がテンプレートに展開される | ✅ |
| 91 | `test_multiple_rules_all_matching_all_executed` | 複数ルールが全てマッチ・実行される | ✅ |
| 92 | `test_rule_from_different_project_not_applied` | 別プロジェクトのルールは適用されない | ❌ |

---

### シグナル層

#### SignalTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 93 | `test_comment_saved_triggers_rules` | コメント保存がルール処理を起動する | ✅ |
| 94 | `test_comment_without_task_does_not_raise` | `task=None` のコメント保存でも例外が発生しない | ❌ |
| 95 | `test_task_saved_triggers_rules_via_description` | タスク保存がルール処理を起動する | ✅ |
| 96 | `test_signal_exception_does_not_propagate` | ルール処理中の例外がシグナルから伝播しない | ❌ |

#### AssignRuleIntegrationTest（ASSIGN ルール統合）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 97 | `test_assign_rule_changes_assignee` | パターン一致で ASSIGN ルールが実行され担当者が変わる | ✅ |
| 98 | `test_assign_rule_no_match_preserves_assignee` | パターン不一致では担当者が変わらない | ❌ |
| 99 | `test_assign_rule_disabled_preserves_assignee` | 無効ルールでは担当者が変わらない | ❌ |
| 100 | `test_assign_rule_nonexistent_user_preserves_assignee` | 存在しないユーザー名では担当者が変わらない | ❌ |
| 101 | `test_task_save_triggers_assign_rule` | タスク保存シグナルで ASSIGN ルールが実行される | ✅ |
| 102 | `test_task_save_no_match_preserves_assignee` | タスク保存でパターン不一致なら担当者が変わらない | ❌ |
| 103 | `test_comment_save_triggers_assign_rule` | コメント保存シグナルで ASSIGN ルールが実行される | ✅ |
| 104 | `test_comment_save_no_match_preserves_assignee` | コメント保存でパターン不一致なら担当者が変わらない | ❌ |

---

### フォーム層

#### TaskFormTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 105 | `test_done_status_with_no_subtasks_is_valid` | サブタスクなしで完了ステータスに変更できる | ✅ |
| 106 | `test_done_status_with_all_subtasks_done_is_valid` | 全サブタスク完了なら親も完了にできる | ✅ |
| 107 | `test_done_status_with_incomplete_subtask_is_invalid` | 未完了サブタスクがあると完了ステータスにできない | ❌ |
| 108 | `test_open_status_with_incomplete_subtask_is_valid` | 未完了ステータスへの変更は常に有効 | ✅ |
| 109 | `test_deadline_field_is_optional` | `deadline` は空でも有効 | ✅ |

#### TaskFormEventTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 110 | `test_event_field_is_present` | フォームに `event` フィールドが存在する | ✅ |
| 111 | `test_event_field_is_not_required` | `event` フィールドは任意入力 | ✅ |
| 112 | `test_form_valid_without_event` | event 未選択でもフォームが有効 | ✅ |
| 113 | `test_event_queryset_includes_own_event` | 自分が参加するプロジェクトの Event が選択肢に含まれる | ✅ |
| 114 | `test_event_queryset_excludes_other_users_event` | 他ユーザーのプロジェクトの Event は選択肢に含まれない | ❌ |
| 115 | `test_form_valid_with_event` | event を選択してもフォームが有効 | ✅ |

#### TaskFormStatusFilterTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 116 | `test_status_queryset_shows_only_project_statuses` | status フィールドにプロジェクトのステータスのみ表示される | ✅ |
| 117 | `test_status_queryset_excludes_other_project_statuses` | 別プロジェクトのステータスは選択肢に含まれない | ❌ |
| 118 | `test_status_queryset_excludes_project_less_statuses` | project なし（nullable）のステータスは含まれない | ❌ |
| 119 | `test_status_queryset_all_when_no_project` | project=None のとき全ステータスが選択肢になる | ✅ |

---

### ビュー層

#### SignUpViewTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 120 | `test_get_returns_200` | GET でサインアップフォームが表示される | ✅ |
| 121 | `test_valid_post_creates_user_and_redirects` | 正常なPOSTでユーザー作成・ログイン・リダイレクト | ✅ |
| 122 | `test_invalid_post_redisplays_form` | パスワード不一致でフォーム再表示・ユーザー未作成 | ❌ |

#### ProjectViewsTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 123 | `test_project_list_requires_login` | 未ログインでログイン画面へリダイレクト | ❌ |
| 124 | `test_project_list_shows_own_projects` | 自分が参加しているプロジェクトが表示される | ✅ |
| 125 | `test_project_list_hides_others_projects` | 他ユーザーのプロジェクトは表示されない | ❌ |
| 126 | `test_project_detail_own` | 自分が参加しているプロジェクト詳細を見られる | ✅ |
| 127 | `test_project_detail_other_returns_404` | 他ユーザーのプロジェクト詳細は 404 | ❌ |
| 128 | `test_project_detail_with_status_filter` | ステータスフィルターがコンテキストに反映される | ✅ |
| 129 | `test_project_create_adds_user_as_participant` | プロジェクト作成後に作成者が participants に追加される | ✅ |
| 130 | `test_project_create_redirects_to_detail` | プロジェクト作成後に詳細ページへリダイレクト | ✅ |
| 131 | `test_project_update_own` | 自分のプロジェクトを更新できる | ✅ |
| 132 | `test_project_update_other_returns_404` | 他ユーザーのプロジェクト更新は 404 | ❌ |
| 133 | `test_project_delete_own` | 自分のプロジェクトを削除できる | ✅ |
| 134 | `test_project_delete_other_returns_404` | 他ユーザーのプロジェクト削除は 404・DB に残る | ❌ |

#### StatusViewsTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 135 | `test_status_list` | ステータス一覧が 200 | ✅ |
| 136 | `test_status_detail` | ステータス詳細が 200 | ✅ |
| 137 | `test_status_create` | プロジェクトスコープ URL で新しいステータスが作成される | ✅ |
| 138 | `test_status_create_sets_project` | 作成したステータスにプロジェクトが紐づく | ✅ |
| 139 | `test_status_create_redirects_to_project_detail` | 作成後にプロジェクト詳細（`#tab-status`）へリダイレクト | ✅ |
| 140 | `test_status_create_other_project_returns_404` | 非参加プロジェクトのステータス作成は 404 | ❌ |
| 141 | `test_status_update` | name と is_done を更新できる | ✅ |
| 142 | `test_status_update_redirects_to_project_detail` | 更新後にプロジェクト詳細（`#tab-status`）へリダイレクト | ✅ |
| 143 | `test_status_delete` | ステータスを削除できる | ✅ |
| 144 | `test_status_delete_redirects_to_project_detail` | 削除後にプロジェクト詳細（`#tab-status`）へリダイレクト | ✅ |
| 145 | `test_status_list_requires_login` | 未ログインでログイン画面へリダイレクト | ❌ |

#### ProjectDetailStatusContextTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 146 | `test_status_list_contains_own_project_statuses` | `status_list` コンテキストにそのプロジェクトのステータスが含まれる | ✅ |
| 147 | `test_status_list_excludes_other_project_statuses` | 別プロジェクトのステータスは `status_list` に含まれない | ❌ |
| 148 | `test_status_filter_uses_project_active_statuses` | `status_filter` にプロジェクトの進行中ステータス ID が含まれる | ✅ |
| 149 | `test_status_filter_excludes_done_statuses` | `status_filter` に完了ステータスの ID は含まれない | ❌ |

#### TaskViewsTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 150 | `test_task_list_requires_login` | 未ログインでログイン画面へリダイレクト | ❌ |
| 151 | `test_task_list_annotation_clashes_with_model_property` | 🐛 TaskListView のアノテーション名が @property と衝突し 500 | 🐛 |
| 152 | `test_task_list_with_status_filter_annotation_bug` | 🐛 ステータスフィルター付きでも同様に 500 | 🐛 |
| 153 | `test_task_detail_accessible_by_assignee` | 担当者本人がタスク詳細を見られる | ✅ |
| 154 | `test_task_detail_accessible_by_project_participant` | プロジェクト参加者もタスク詳細を見られる | ✅ |
| 155 | `test_task_detail_inaccessible_by_unrelated_user` | 無関係ユーザーには 404 | ❌ |
| 156 | `test_task_detail_breadcrumbs_include_ancestors` | 子タスク詳細のパンくずに親・子の順で含まれる | ✅ |
| 157 | `test_task_detail_breadcrumbs_root_task` | ルートタスクのパンくずは自分自身のみ | ✅ |
| 158 | `test_task_create_with_project_param_sets_project` | `?project=` パラメータでプロジェクトが設定される | ✅ |
| 159 | `test_task_create_sets_assignee_to_current_user` | タスク作成時の担当者がログインユーザーになる | ✅ |
| 160 | `test_task_create_with_parent_param_sets_parent` | `?task=` パラメータで parent と project が設定される | ✅ |
| 161 | `test_task_create_done_status_sets_completed_at` | 完了ステータスで作成すると `completed_at` が設定される | ✅ |
| 162 | `test_task_create_open_status_leaves_completed_at_null` | 未完了ステータスで作成すると `completed_at` が NULL | ✅ |
| 163 | `test_task_create_unrelated_project_param_returns_500` | 🐛 非参加プロジェクト指定時に project 未設定で IntegrityError → 500 | 🐛 |
| 164 | `test_task_update_sets_completed_at_when_done` | 完了ステータスに更新すると `completed_at` が設定される | ✅ |
| 165 | `test_task_update_clears_completed_at_when_not_done` | 未完了ステータスに戻すと `completed_at` が NULL になる | ✅ |
| 166 | `test_task_delete_removes_task` | タスクを削除できる | ✅ |
| 167 | `test_task_watch_adds_to_watches` | ウォッチ追加でユーザーの watches に入る | ✅ |
| 168 | `test_task_unwatch_removes_from_watches` | ウォッチ解除で watches から外れる | ✅ |
| 169 | `test_task_watch_unrelated_task_has_no_effect` | 無関係タスクをウォッチしても watches に追加されない | ❌ |
| 170 | `test_task_watch_requires_login` | 未ログインでリダイレクト・ウォッチ追加されない | ❌ |

#### TaskEventViewsTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 171 | `test_task_create_with_event_sets_event` | タスク作成時に event を紐づけできる | ✅ |
| 172 | `test_task_create_without_event_leaves_null` | event 未選択でタスク作成すると `event` が NULL | ✅ |
| 173 | `test_task_update_sets_event` | タスク更新で event を紐づけできる | ✅ |
| 174 | `test_task_update_clears_event` | タスク更新で event を解除できる | ✅ |

#### CommentViewsTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 175 | `test_comment_list_requires_login` | 未ログインでログイン画面へリダイレクト | ❌ |
| 176 | `test_comment_list_template_references_undefined_task_variable` | 🐛 テンプレートが未定義変数 `task` を参照し 500 | 🐛 |
| 177 | `test_comment_detail_accessible_by_author` | 投稿者本人がコメント詳細を見られる | ✅ |
| 178 | `test_comment_detail_accessible_by_participant` | プロジェクト参加者もコメント詳細を見られる | ✅ |
| 179 | `test_comment_detail_inaccessible_by_unrelated_user` | 無関係ユーザーには 404 | ❌ |
| 180 | `test_comment_create_sets_author` | コメント作成時の author がログインユーザーになる | ✅ |
| 181 | `test_comment_create_get_with_task_param_prefills_initial` | `?task=` パラメータでフォームの initial が設定される | ✅ |
| 182 | `test_comment_update_own` | 自分のコメントを更新できる | ✅ |
| 183 | `test_comment_update_by_unrelated_user_returns_404` | 無関係ユーザーによる更新は 404 | ❌ |
| 184 | `test_comment_delete_own` | 自分のコメントを削除できる | ✅ |
| 185 | `test_comment_delete_by_unrelated_user_returns_404` | 無関係ユーザーによる削除は 404・DB に残る | ❌ |

---

### ガントチャートフィルタ

#### BuildGanttDataFilterTest（`build_gantt_data` 直接テスト）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 186 | `test_status_filter_active_excludes_done_tasks` | `status_filter='active'` で完了タスクを除外する | ❌ |
| 187 | `test_status_filter_active_includes_open_tasks` | `status_filter='active'` で進行中タスクを含む | ✅ |
| 188 | `test_status_filter_done_excludes_open_tasks` | `status_filter='done'` で進行中タスクを除外する | ❌ |
| 189 | `test_status_filter_done_includes_done_tasks` | `status_filter='done'` で完了タスクを含む | ✅ |
| 190 | `test_status_filter_all_includes_all_tasks` | `status_filter='all'` で全タスクを含む | ✅ |
| 191 | `test_assignee_ids_filters_to_specified_user` | `assignee_ids` に指定したユーザーのタスクのみ表示する | ❌ |
| 192 | `test_assignee_ids_none_shows_all_users` | `assignee_ids=None` で全ユーザーのタスクを表示する | ✅ |
| 193 | `test_assignee_ids_multiple_users` | 複数の `assignee_ids` を指定すると全員のタスクを含む | ✅ |
| 194 | `test_assignee_and_status_filter_combined` | `assignee_ids` と `status_filter` を組み合わせたフィルタが機能する | ✅ |

#### GanttFilterViewTest（ビューレベルのガントフィルタ）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 195 | `test_gantt_default_hides_done_tasks` | デフォルト表示で完了タスクが非表示になる | ❌ |
| 196 | `test_gantt_default_shows_own_active_tasks` | デフォルト表示で自分の進行中タスクが表示される | ✅ |
| 197 | `test_gantt_default_hides_other_users_tasks` | デフォルト表示で他ユーザーのタスクが非表示になる | ❌ |
| 198 | `test_gantt_status_all_shows_done_tasks` | `gantt_status=all` で完了タスクが表示される | ✅ |
| 199 | `test_gantt_status_done_shows_only_done_tasks` | `gantt_status=done` で完了タスクのみが表示される | ✅ |
| 200 | `test_gantt_assignees_param_filters_by_username` | `gantt_assignees=<username>` でそのユーザーのタスクのみ表示される | ✅ |
| 201 | `test_gantt_context_contains_gantt_status` | コンテキストに `gantt_status` が格納される | ✅ |
| 202 | `test_gantt_invalid_status_falls_back_to_active` | 不正な `gantt_status` 値は `'active'` にフォールバックする | ❌ |
| 203 | `test_gantt_context_contains_gantt_assignees` | コンテキストに `gantt_assignees` が格納される | ✅ |

---

## event_app

### モデル層

#### ItemModelTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 204 | `test_str` | `__str__` が "company name" を返す | ✅ |
| 205 | `test_count_per_case_default_is_one` | `count_per_case` のデフォルト値が 1 | ✅ |
| 206 | `test_company_and_name_can_be_blank` | company・name が空でも作成できる | ✅ |

#### InventoryModelTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 207 | `test_str` | `__str__` が name を返す | ✅ |
| 208 | `test_unique_together_item_inventory_raises_on_duplicate` | 同じ item × inventory の組み合わせは IntegrityError | ❌ |
| 209 | `test_previous_inventory_link` | `previous_inventory` と `next_inventory` の双方向リンク | ✅ |

#### EventModelTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 210 | `test_previous_event_link` | `previous_event` と `next_event` の双方向リンク | ✅ |
| 211 | `test_previous_event_is_optional` | `previous_event` がデフォルト NULL | ✅ |
| 212 | `test_participant_count_is_optional` | `participant_count` がデフォルト NULL | ✅ |
| 213 | `test_str_with_name` | name あり Event の `__str__` が "日付 名前" 形式 | ✅ |
| 214 | `test_str_without_name` | name なし Event の `__str__` が "日付" のみ | ✅ |

---

### ビジネスロジック層

#### GetPreviousDifferenceTest（`Inventory.get_previous_difference`）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 215 | `test_single_item_counts_returned_correctly` | 今回・前回の case_count / item_count が正しく返る | ✅ |
| 216 | `test_no_previous_inventory_has_no_previous_counts` | 前回インベントリなしでも今回の値は返る | ✅ |
| 217 | `test_multiple_items_all_returned` | 複数アイテムが全件返る | ✅ |
| 218 | `test_item_only_in_current_has_null_previous` | 今回のみのアイテムは previous_* が NULL | ❌ |
| 219 | `test_item_only_in_previous_has_null_current` | 前回のみのアイテムは current_* が NULL | ❌ |
| 220 | `test_item_unchanged_still_returned` | 変化のないアイテムも返る（今回 = 前回） | ✅ |
| 221 | `test_empty_inventory_returns_empty_queryset` | アイテムなしで空のクエリセットが返る | ✅ |

---

### ビュー層

#### EventViewsTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 222 | `test_event_list_requires_login` | 未ログインでログイン画面へリダイレクト | ❌ |
| 223 | `test_event_list_template_does_not_exist` | 🐛 `event_list.html` が存在せず 500 | 🐛 |
| 224 | `test_event_detail_own` | 自分のイベント詳細が 200 | ✅ |
| 225 | `test_event_detail_requires_login` | 未ログインでログイン画面へリダイレクト | ❌ |
| 226 | `test_event_detail_other_returns_404` | 他ユーザーのイベント詳細は 404 | ❌ |
| 227 | `test_event_create_get_returns_200` | イベント作成フォームが 200 | ✅ |
| 228 | `test_event_create_with_previous_param_prefills_form` | `?previous=` で `previous_event` が initial に設定される | ✅ |
| 229 | `test_event_create_post_creates_event` | 正常なPOSTでイベントが作成される | ✅ |
| 230 | `test_event_update_changes_date` | イベントの `event_date` を更新できる | ✅ |
| 231 | `test_event_update_other_returns_404` | 他ユーザーのイベント更新は 404 | ❌ |
| 232 | `test_event_delete_removes_event` | イベントを削除できる | ✅ |
| 233 | `test_event_delete_other_returns_404` | 他ユーザーのイベント削除は 404・DB に残る | ❌ |
| 234 | `test_event_detail_shows_linked_task` | 詳細画面に紐づけたタスクのタイトルが表示される | ✅ |
| 235 | `test_event_detail_excludes_unlinked_task` | 紐づけていないタスクは詳細画面に表示されない | ❌ |
| 236 | `test_event_detail_shows_no_tasks_message_when_empty` | タスクが未登録の場合に空メッセージが表示される | ✅ |

#### InventoryViewsTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 237 | `test_inventory_list_requires_login` | 未ログインでログイン画面へリダイレクト | ❌ |
| 238 | `test_inventory_list_template_does_not_exist` | 🐛 `inventory_list.html` が存在せず 500 | 🐛 |
| 239 | `test_inventory_detail_returns_200` | 自分のインベントリ詳細が 200 | ✅ |
| 240 | `test_inventory_detail_context_includes_items` | 詳細コンテキストに `items`（差分）が含まれる | ✅ |
| 241 | `test_inventory_detail_other_returns_404` | 他ユーザーのインベントリ詳細は 404 | ❌ |
| 242 | `test_inventory_create_get_with_previous_param_prefills_form` | `?previous=` で `previous_inventory` が initial に設定される | ✅ |
| 243 | `test_inventory_create_get_with_previous_clears_name` | `?previous=` 指定時に name が空文字でリセットされる | ✅ |
| 244 | `test_inventory_update_get_returns_200` | 自分のインベントリ更新フォームが 200 | ✅ |
| 245 | `test_inventory_update_other_returns_404` | 他ユーザーのインベントリ更新フォームは 404 | ❌ |
| 246 | `test_inventory_delete_removes_inventory` | インベントリを削除できる | ✅ |
| 247 | `test_inventory_delete_other_returns_404` | 他ユーザーのインベントリ削除は 404・DB に残る | ❌ |

---

## 既知バグ一覧（🐛 テストで文書化済み）

| バグ | 影響箇所 | テスト # |
|------|---------|---------|
| `TaskListView` が `completed_subtask_count` / `total_subtask_count` アノテーション名を Task の `@property` と同名で定義しており、クエリセット反復時に `AttributeError` で 500 | `task_list` 画面 | 151, 152 |
| プロジェクト作成で非参加プロジェクトの `?project=` を指定した場合、`project_id` が NULL のまま保存されて `IntegrityError` が発生し 500 | タスク作成画面 | 163 |
| `comment_list_component.html` が未定義変数 `task` を参照（`{{ comment.description\|markdown:task.project }}`）しており 500 | コメント一覧画面 | 176 |
| `event_app/event_list.html` テンプレートが存在しない | イベント一覧画面 | 223 |
| `event_app/inventory_list.html` テンプレートが存在しない | インベントリ一覧画面 | 238 |

---

## 集計

| カテゴリ | 件数 |
|---------|-----|
| モデル層（task_app） | 38 |
| DSL 層（parse） | 8 |
| DSL 層（grammar） | 10 |
| DSL 層（execute） | 21 |
| ルール処理層 | 9 |
| シグナル層 | 4 |
| ASSIGN ルール統合 | 8 |
| フォーム層 | 15 |
| ビュー層（task_app） | 62 |
| ガントチャートフィルタ | 18 |
| モデル層（event_app） | 11 |
| ビジネスロジック層（event_app） | 7 |
| ビュー層（event_app） | 26 |
| **合計** | **247** |

| 種別 | 件数 |
|------|-----|
| ✅ 正常系 | 144 |
| ❌ 異常系・境界値 | 98 |
| 🐛 既知バグ文書化 | 5 |
