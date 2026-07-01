# 詳細設計：タスク種別 × タスクステータスの組み合わせでの Agent Script 設定

対象タスク: #476（【開発】【詳細設計】種別×ステータス別に Agent Script を設定可能にする詳細設計）
関連タスク: #474（対応方針検討／基本設計）

## 前提と設計方針

現状、Agent Script は `TaskType.agent`（タスク種別単位）にのみ設定でき、
`claude-agent/agent.py` の `_resolve_agent_script()` が種別単位でスクリプトを
解決している。これを「種別 × ステータス（状態指定型）」の組み合わせで解決できる
よう拡張する。

**採用方針（状態指定型）**: 確認事項では遷移型／状態型が未確定だが、既存のトリガー
（`assignee` を Automation に変更した時点で SQS→ECS 起動）が「その時点のタスク状態」
を渡す構造のため、実装コストと後方互換性の観点から **状態指定型**（タスクの現在
ステータスをキーとする）を推奨する。ステータス未指定のスクリプトは全ステータス共通の
フォールバックとして扱い、既存の `TaskType.agent` を「ステータス未指定」の互換設定
として温存する。

---

## 変更ファイル対応表

### 1. データモデル層

| ファイルパス | 変更種別 | 変更内容 |
|---|---|---|
| `django-app/task_app/models.py` | 変更 | 新規モデル `TaskTypeStatusAgent` を追加。`task_type`（FK→`TaskType`）、`status`（FK→`Status`, null 許容）、`agent`（TextField）を持たせ、`unique_together = [('task_type', 'status')]` を設定。`status=null` を「全ステータス共通（既存 `TaskType.agent` 相当）」の位置づけとする。`related_name='status_agents'` を付与。`auditlog.register(TaskTypeStatusAgent)` を末尾に追加。 |
| `django-app/task_app/migrations/000X_tasktypestatusagent.py` | 新規 | 上記モデル追加のマイグレーション（新規ファイル）。`makemigrations` により自動生成。 |

> 備考: `TaskType.agent` フィールドは後方互換のため残す（削除しない）。データ移行が
> 必要な場合は同マイグレーション内でデータマイグレーションを追加検討する。

想定モデル定義（抜粋）:

