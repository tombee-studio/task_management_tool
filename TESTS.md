# テストケース一覧

合計 **166 件** のテストケース（task_app: 127 件 / event_app: 39 件）

**最終パス確認: 2026-05-25 JST** — `Ran 166 tests in 31.312s` → **OK**

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

#### RuleModelTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 15 | `test_str` | `__str__` が "プロジェクト名: ルール名" を返す | ✅ |
| 16 | `test_enabled_default_true` | `enabled` のデフォルト値が True | ✅ |

---

### DSL 層

#### DSLParseTest（`parse_dsl`）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 17 | `test_single_link` | 1 行の LINK コマンドをパースできる | ✅ |
| 18 | `test_multiple_links` | 複数行の LINK を全てパースできる | ✅ |
| 19 | `test_empty_text` | 空文字列で空リストを返す | ❌ |
| 20 | `test_no_link_command` | LINK を含まない行は無視される | ❌ |
| 21 | `test_case_insensitive` | 小文字の `link` も認識する | ❌ |
| 22 | `test_extra_whitespace_between_tokens` | トークン間の余分な空白を許容する | ❌ |
| 23 | `test_non_link_lines_are_ignored` | LINK 以外の行は無視される | ❌ |
| 24 | `test_returns_correct_ids` | AST に src_id / dst_id が正しく格納される | ✅ |

#### DSLExecuteTest（`execute_dsl` / `execute_link`）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 25 | `test_creates_relation` | LINK 実行で `related_tasks` に関係が追加される | ✅ |
| 26 | `test_nonexistent_task_does_not_raise` | 存在しない Task ID でも例外が発生しない | ❌ |
| 27 | `test_idempotent` | 同じ LINK を 2 回実行しても重複しない | ❌ |
| 28 | `test_execute_link_directly` | `execute_link` を直接呼んでも関係が作成される | ✅ |
| 29 | `test_execute_link_nonexistent_src_does_not_raise` | src が存在しなくても例外が発生しない | ❌ |
| 30 | `test_execute_link_nonexistent_dst_does_not_raise` | dst が存在しなくても例外が発生しない | ❌ |
| 31 | `test_execute_link_both_nonexistent_does_not_raise` | src・dst 両方存在しなくても例外が発生しない | ❌ |
| 32 | `test_multiple_links_in_one_dsl` | 1 DSL に複数 LINK を含む場合に全て実行される | ✅ |

#### DSLExecuteAssignTest（`execute_dsl` / `execute_assign`）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 33 | `test_assign_changes_assignee` | ASSIGN 実行でタスクの担当者が変更される | ✅ |
| 34 | `test_assign_quoted_username` | クォートされたユーザー名でも担当者を変更できる | ✅ |
| 35 | `test_assign_nonexistent_task_does_not_raise` | 存在しない Task ID でも例外が発生しない | ❌ |
| 36 | `test_assign_nonexistent_user_does_not_raise` | 存在しないユーザー名でも例外が発生せず担当者は変わらない | ❌ |
| 37 | `test_execute_assign_directly` | `execute_assign` を直接呼んでも担当者が変更される | ✅ |

#### DSLGrammarTest（LARK 文法 — パースのみ）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 38 | `test_tag_bare_name` | TAG に裸の識別子を渡すとパースできる | ✅ |
| 39 | `test_tag_quoted_string` | TAG にクォート文字列（スペース含む）を渡すとパースできる | ✅ |
| 40 | `test_tag_case_insensitive` | 小文字の `tag` も認識する | ❌ |
| 41 | `test_parent_basic` | PARENT コマンドを `->` 記法でパースできる | ✅ |
| 42 | `test_parent_case_insensitive` | 小文字の `parent` も認識する | ❌ |
| 43 | `test_assign_bare_username` | ASSIGN に裸のユーザー名を渡すとパースできる | ✅ |
| 44 | `test_assign_quoted_username` | ASSIGN にクォート文字列（スペース含む）を渡すとパースできる | ✅ |
| 45 | `test_assign_case_insensitive` | 小文字の `assign` / `to` も認識する | ❌ |
| 46 | `test_mixed_commands_in_one_dsl` | LINK・TAG・PARENT・ASSIGN を 1 DSL に混在させてパースできる | ✅ |
| 47 | `test_unknown_commands_ignored_mixed` | 未知行を含む DSL でも既知コマンドのみがパースされる | ❌ |

---

### ルール処理層

#### RulesProcessTest（`process_task_rules`）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 48 | `test_no_rules_no_effect` | ルールがなければ related_tasks は変化しない | ✅ |
| 49 | `test_pattern_no_match_no_dsl` | パターン不一致ではDSLが実行されない | ❌ |
| 50 | `test_disabled_rule_is_ignored` | `enabled=False` のルールは無視される | ❌ |
| 51 | `test_enabled_rule_with_match_links_tasks` | パターン一致でDSLが実行されタスクが繋がる | ✅ |
| 52 | `test_uses_task_description_when_no_text_given` | `text` 省略時はタスクの description を使用する | ✅ |
| 53 | `test_text_param_overrides_description` | `text` 引数が description より優先される | ✅ |
| 54 | `test_task_id_is_substituted_in_template` | `{task_id}` がテンプレートに展開される | ✅ |
| 55 | `test_multiple_rules_all_matching_all_executed` | 複数ルールが全てマッチ・実行される | ✅ |
| 56 | `test_rule_from_different_project_not_applied` | 別プロジェクトのルールは適用されない | ❌ |

---

### シグナル層

#### SignalTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 57 | `test_comment_saved_triggers_rules` | コメント保存がルール処理を起動する | ✅ |
| 58 | `test_comment_without_task_does_not_raise` | `task=None` のコメント保存でも例外が発生しない | ❌ |
| 59 | `test_task_saved_triggers_rules_via_description` | タスク保存がルール処理を起動する | ✅ |
| 60 | `test_signal_exception_does_not_propagate` | ルール処理中の例外がシグナルから伝播しない | ❌ |

#### AssignRuleIntegrationTest（ASSIGN ルール統合）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 61 | `test_assign_rule_changes_assignee` | パターン一致で ASSIGN ルールが実行され担当者が変わる | ✅ |
| 62 | `test_assign_rule_no_match_preserves_assignee` | パターン不一致では担当者が変わらない | ❌ |
| 63 | `test_assign_rule_disabled_preserves_assignee` | 無効ルールでは担当者が変わらない | ❌ |
| 64 | `test_assign_rule_nonexistent_user_preserves_assignee` | 存在しないユーザー名では担当者が変わらない | ❌ |
| 65 | `test_task_save_triggers_assign_rule` | タスク保存シグナルで ASSIGN ルールが実行される | ✅ |
| 66 | `test_task_save_no_match_preserves_assignee` | タスク保存でパターン不一致なら担当者が変わらない | ❌ |
| 67 | `test_comment_save_triggers_assign_rule` | コメント保存シグナルで ASSIGN ルールが実行される | ✅ |
| 68 | `test_comment_save_no_match_preserves_assignee` | コメント保存でパターン不一致なら担当者が変わらない | ❌ |

---

### フォーム層

#### TaskFormTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 69 | `test_done_status_with_no_subtasks_is_valid` | サブタスクなしで完了ステータスに変更できる | ✅ |
| 70 | `test_done_status_with_all_subtasks_done_is_valid` | 全サブタスク完了なら親も完了にできる | ✅ |
| 71 | `test_done_status_with_incomplete_subtask_is_invalid` | 未完了サブタスクがあると完了ステータスにできない | ❌ |
| 72 | `test_open_status_with_incomplete_subtask_is_valid` | 未完了ステータスへの変更は常に有効 | ✅ |
| 73 | `test_deadline_field_is_optional` | `deadline` は空でも有効 | ✅ |

---

### ビュー層

#### SignUpViewTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 74 | `test_get_returns_200` | GET でサインアップフォームが表示される | ✅ |
| 75 | `test_valid_post_creates_user_and_redirects` | 正常なPOSTでユーザー作成・ログイン・リダイレクト | ✅ |
| 76 | `test_invalid_post_redisplays_form` | パスワード不一致でフォーム再表示・ユーザー未作成 | ❌ |

#### ProjectViewsTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 77 | `test_project_list_requires_login` | 未ログインでログイン画面へリダイレクト | ❌ |
| 78 | `test_project_list_shows_own_projects` | 自分が参加しているプロジェクトが表示される | ✅ |
| 79 | `test_project_list_hides_others_projects` | 他ユーザーのプロジェクトは表示されない | ❌ |
| 80 | `test_project_detail_own` | 自分が参加しているプロジェクト詳細を見られる | ✅ |
| 81 | `test_project_detail_other_returns_404` | 他ユーザーのプロジェクト詳細は 404 | ❌ |
| 82 | `test_project_detail_with_status_filter` | ステータスフィルターがコンテキストに反映される | ✅ |
| 83 | `test_project_create_adds_user_as_participant` | プロジェクト作成後に作成者が participants に追加される | ✅ |
| 84 | `test_project_create_redirects_to_detail` | プロジェクト作成後に詳細ページへリダイレクト | ✅ |
| 85 | `test_project_update_own` | 自分のプロジェクトを更新できる | ✅ |
| 86 | `test_project_update_other_returns_404` | 他ユーザーのプロジェクト更新は 404 | ❌ |
| 87 | `test_project_delete_own` | 自分のプロジェクトを削除できる | ✅ |
| 88 | `test_project_delete_other_returns_404` | 他ユーザーのプロジェクト削除は 404・DB に残る | ❌ |

#### StatusViewsTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 89 | `test_status_list` | ステータス一覧が 200 | ✅ |
| 90 | `test_status_detail` | ステータス詳細が 200 | ✅ |
| 91 | `test_status_create` | 新しいステータスが作成される | ✅ |
| 92 | `test_status_create_redirects` | 作成後にプロジェクト一覧へリダイレクト | ✅ |
| 93 | `test_status_update` | name と is_done を更新できる | ✅ |
| 94 | `test_status_delete` | ステータスを削除できる | ✅ |
| 95 | `test_status_list_requires_login` | 未ログインでログイン画面へリダイレクト | ❌ |

#### TaskViewsTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 96 | `test_task_list_requires_login` | 未ログインでログイン画面へリダイレクト | ❌ |
| 97 | `test_task_list_annotation_clashes_with_model_property` | 🐛 TaskListView のアノテーション名が @property と衝突し 500 | 🐛 |
| 98 | `test_task_list_with_status_filter_annotation_bug` | 🐛 ステータスフィルター付きでも同様に 500 | 🐛 |
| 99 | `test_task_detail_accessible_by_assignee` | 担当者本人がタスク詳細を見られる | ✅ |
| 100 | `test_task_detail_accessible_by_project_participant` | プロジェクト参加者もタスク詳細を見られる | ✅ |
| 101 | `test_task_detail_inaccessible_by_unrelated_user` | 無関係ユーザーには 404 | ❌ |
| 102 | `test_task_detail_breadcrumbs_include_ancestors` | 子タスク詳細のパンくずに親・子の順で含まれる | ✅ |
| 103 | `test_task_detail_breadcrumbs_root_task` | ルートタスクのパンくずは自分自身のみ | ✅ |
| 104 | `test_task_create_with_project_param_sets_project` | `?project=` パラメータでプロジェクトが設定される | ✅ |
| 105 | `test_task_create_sets_assignee_to_current_user` | タスク作成時の担当者がログインユーザーになる | ✅ |
| 106 | `test_task_create_with_parent_param_sets_parent` | `?task=` パラメータで parent と project が設定される | ✅ |
| 107 | `test_task_create_done_status_sets_completed_at` | 完了ステータスで作成すると `completed_at` が設定される | ✅ |
| 108 | `test_task_create_open_status_leaves_completed_at_null` | 未完了ステータスで作成すると `completed_at` が NULL | ✅ |
| 109 | `test_task_create_unrelated_project_param_returns_500` | 🐛 非参加プロジェクト指定時に project 未設定で IntegrityError → 500 | 🐛 |
| 110 | `test_task_update_sets_completed_at_when_done` | 完了ステータスに更新すると `completed_at` が設定される | ✅ |
| 111 | `test_task_update_clears_completed_at_when_not_done` | 未完了ステータスに戻すと `completed_at` が NULL になる | ✅ |
| 112 | `test_task_delete_removes_task` | タスクを削除できる | ✅ |
| 113 | `test_task_watch_adds_to_watches` | ウォッチ追加でユーザーの watches に入る | ✅ |
| 114 | `test_task_unwatch_removes_from_watches` | ウォッチ解除で watches から外れる | ✅ |
| 115 | `test_task_watch_unrelated_task_has_no_effect` | 無関係タスクをウォッチしても watches に追加されない | ❌ |
| 116 | `test_task_watch_requires_login` | 未ログインでリダイレクト・ウォッチ追加されない | ❌ |

#### CommentViewsTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 117 | `test_comment_list_requires_login` | 未ログインでログイン画面へリダイレクト | ❌ |
| 118 | `test_comment_list_template_references_undefined_task_variable` | 🐛 テンプレートが未定義変数 `task` を参照し 500 | 🐛 |
| 119 | `test_comment_detail_accessible_by_author` | 投稿者本人がコメント詳細を見られる | ✅ |
| 120 | `test_comment_detail_accessible_by_participant` | プロジェクト参加者もコメント詳細を見られる | ✅ |
| 121 | `test_comment_detail_inaccessible_by_unrelated_user` | 無関係ユーザーには 404 | ❌ |
| 122 | `test_comment_create_sets_author` | コメント作成時の author がログインユーザーになる | ✅ |
| 123 | `test_comment_create_get_with_task_param_prefills_initial` | `?task=` パラメータでフォームの initial が設定される | ✅ |
| 124 | `test_comment_update_own` | 自分のコメントを更新できる | ✅ |
| 125 | `test_comment_update_by_unrelated_user_returns_404` | 無関係ユーザーによる更新は 404 | ❌ |
| 126 | `test_comment_delete_own` | 自分のコメントを削除できる | ✅ |
| 127 | `test_comment_delete_by_unrelated_user_returns_404` | 無関係ユーザーによる削除は 404・DB に残る | ❌ |

---

## event_app

### モデル層

#### ItemModelTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 128 | `test_str` | `__str__` が "company name" を返す | ✅ |
| 129 | `test_count_per_case_default_is_one` | `count_per_case` のデフォルト値が 1 | ✅ |
| 130 | `test_company_and_name_can_be_blank` | company・name が空でも作成できる | ✅ |

#### InventoryModelTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 131 | `test_str` | `__str__` が name を返す | ✅ |
| 132 | `test_unique_together_item_inventory_raises_on_duplicate` | 同じ item × inventory の組み合わせは IntegrityError | ❌ |
| 133 | `test_previous_inventory_link` | `previous_inventory` と `next_inventory` の双方向リンク | ✅ |

#### EventModelTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 134 | `test_previous_event_link` | `previous_event` と `next_event` の双方向リンク | ✅ |
| 135 | `test_previous_event_is_optional` | `previous_event` がデフォルト NULL | ✅ |
| 136 | `test_participant_count_is_optional` | `participant_count` がデフォルト NULL | ✅ |

---

### ビジネスロジック層

#### GetPreviousDifferenceTest（`Inventory.get_previous_difference`）

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 137 | `test_single_item_counts_returned_correctly` | 今回・前回の case_count / item_count が正しく返る | ✅ |
| 138 | `test_no_previous_inventory_has_no_previous_counts` | 前回インベントリなしでも今回の値は返る | ✅ |
| 139 | `test_multiple_items_all_returned` | 複数アイテムが全件返る | ✅ |
| 140 | `test_item_only_in_current_has_null_previous` | 今回のみのアイテムは previous_* が NULL | ❌ |
| 141 | `test_item_only_in_previous_has_null_current` | 前回のみのアイテムは current_* が NULL | ❌ |
| 142 | `test_item_unchanged_still_returned` | 変化のないアイテムも返る（今回 = 前回） | ✅ |
| 143 | `test_empty_inventory_returns_empty_queryset` | アイテムなしで空のクエリセットが返る | ✅ |

---

### ビュー層

#### EventViewsTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 144 | `test_event_list_requires_login` | 未ログインでログイン画面へリダイレクト | ❌ |
| 145 | `test_event_list_template_does_not_exist` | 🐛 `event_list.html` が存在せず 500 | 🐛 |
| 146 | `test_event_detail_own` | 自分のイベント詳細が 200 | ✅ |
| 147 | `test_event_detail_requires_login` | 未ログインでログイン画面へリダイレクト | ❌ |
| 148 | `test_event_detail_other_returns_404` | 他ユーザーのイベント詳細は 404 | ❌ |
| 149 | `test_event_create_get_returns_200` | イベント作成フォームが 200 | ✅ |
| 150 | `test_event_create_with_previous_param_prefills_form` | `?previous=` で `previous_event` が initial に設定される | ✅ |
| 151 | `test_event_create_post_creates_event` | 正常なPOSTでイベントが作成される | ✅ |
| 152 | `test_event_update_changes_date` | イベントの `event_date` を更新できる | ✅ |
| 153 | `test_event_update_other_returns_404` | 他ユーザーのイベント更新は 404 | ❌ |
| 154 | `test_event_delete_removes_event` | イベントを削除できる | ✅ |
| 155 | `test_event_delete_other_returns_404` | 他ユーザーのイベント削除は 404・DB に残る | ❌ |

#### InventoryViewsTest

| # | テストメソッド | 確認観点 | 種別 |
|---|---------------|---------|------|
| 156 | `test_inventory_list_requires_login` | 未ログインでログイン画面へリダイレクト | ❌ |
| 157 | `test_inventory_list_template_does_not_exist` | 🐛 `inventory_list.html` が存在せず 500 | 🐛 |
| 158 | `test_inventory_detail_returns_200` | 自分のインベントリ詳細が 200 | ✅ |
| 159 | `test_inventory_detail_context_includes_items` | 詳細コンテキストに `items`（差分）が含まれる | ✅ |
| 160 | `test_inventory_detail_other_returns_404` | 他ユーザーのインベントリ詳細は 404 | ❌ |
| 161 | `test_inventory_create_get_with_previous_param_prefills_form` | `?previous=` で `previous_inventory` が initial に設定される | ✅ |
| 162 | `test_inventory_create_get_with_previous_clears_name` | `?previous=` 指定時に name が空文字でリセットされる | ✅ |
| 163 | `test_inventory_update_get_returns_200` | 自分のインベントリ更新フォームが 200 | ✅ |
| 164 | `test_inventory_update_other_returns_404` | 他ユーザーのインベントリ更新フォームは 404 | ❌ |
| 165 | `test_inventory_delete_removes_inventory` | インベントリを削除できる | ✅ |
| 166 | `test_inventory_delete_other_returns_404` | 他ユーザーのインベントリ削除は 404・DB に残る | ❌ |

---

## 既知バグ一覧（🐛 テストで文書化済み）

| バグ | 影響箇所 | テスト # |
|------|---------|---------|
| `TaskListView` が `completed_subtask_count` / `total_subtask_count` アノテーション名を Task の `@property` と同名で定義しており、クエリセット反復時に `AttributeError` で 500 | `task_list` 画面 | 97, 98 |
| プロジェクト作成で非参加プロジェクトの `?project=` を指定した場合、`project_id` が NULL のまま保存されて `IntegrityError` が発生し 500 | タスク作成画面 | 109 |
| `comment_list_component.html` が未定義変数 `task` を参照（`{{ comment.description\|markdown:task.project }}`）しており 500 | コメント一覧画面 | 118 |
| `event_app/event_list.html` テンプレートが存在しない | イベント一覧画面 | 145 |
| `event_app/inventory_list.html` テンプレートが存在しない | インベントリ一覧画面 | 157 |

---

## 集計

| カテゴリ | 件数 |
|---------|-----|
| モデル層 | 16 |
| DSL 層（parse） | 8 |
| DSL 層（execute） | 13 |
| DSL 層（grammar） | 10 |
| ルール処理層 | 9 |
| シグナル層 | 4 |
| ASSIGN ルール統合 | 8 |
| フォーム層 | 5 |
| ビュー層（task_app） | 54 |
| モデル層（event_app） | 9 |
| ビジネスロジック層（event_app） | 7 |
| ビュー層（event_app） | 23 |
| **合計** | **166** |

| 種別 | 件数 |
|------|-----|
| ✅ 正常系 | 98 |
| ❌ 異常系・境界値 | 63 |
| 🐛 既知バグ文書化 | 5 |
