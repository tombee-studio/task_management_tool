from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .dsl import execute_assign, execute_dsl, execute_event, execute_link, parse_dsl
from .filters import apply_task_filters, parse_search_query
from .forms import CommentForm, TaskForm
from .models import Comment, Project, Rule, Status, Tag, Task
from event_app.models import Event
from .rules import process_task_rules

User = get_user_model()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ProjectModelTest(TestCase):
    def test_str(self):
        self.assertEqual(str(Project.objects.create(name="Alpha")), "Alpha")

    def test_participants_m2m(self):
        user = User.objects.create_user(username="u", password="p")
        project = Project.objects.create(name="P")
        project.participants.add(user)
        self.assertIn(user, project.participants.all())


class StatusModelTest(TestCase):
    def test_str(self):
        self.assertEqual(str(Status.objects.create(name="Open")), "Open")

    def test_is_done_default_false(self):
        self.assertFalse(Status.objects.create(name="Pending").is_done)

    def test_is_done_can_be_set_true(self):
        self.assertTrue(Status.objects.create(name="Done", is_done=True).is_done)


class TaskModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.status = Status.objects.create(name="Open")
        self.done = Status.objects.create(name="Done", is_done=True)
        self.project = Project.objects.create(name="P")

    def _task(self, title="T", parent=None, status=None):
        return Task.objects.create(
            title=title,
            project=self.project,
            assignee=self.user,
            status=status or self.status,
            parent=parent,
        )

    def test_str(self):
        self.assertEqual(str(self._task("My Task")), "My Task")

    def test_parent_relationship(self):
        parent = self._task("Parent")
        child = self._task("Child", parent=parent)
        self.assertEqual(child.parent, parent)

    def test_total_subtask_count_zero(self):
        self.assertEqual(self._task().total_subtask_count, 0)

    def test_total_subtask_count_nonzero(self):
        parent = self._task("P")
        self._task("C1", parent=parent)
        self._task("C2", parent=parent)
        self.assertEqual(parent.total_subtask_count, 2)

    def test_completed_subtask_count(self):
        parent = self._task("P")
        self._task("Done", parent=parent, status=self.done)
        self._task("Open", parent=parent)
        self.assertEqual(parent.completed_subtask_count, 1)

    def test_completed_subtask_count_all_done(self):
        parent = self._task("P")
        self._task("D1", parent=parent, status=self.done)
        self._task("D2", parent=parent, status=self.done)
        self.assertEqual(parent.completed_subtask_count, 2)

    def test_related_tasks_symmetrical(self):
        a = self._task("A")
        b = self._task("B")
        a.related_tasks.add(b)
        self.assertIn(a, b.related_tasks.all())

    def test_deadline_optional(self):
        task = self._task()
        self.assertIsNone(task.deadline)

    def test_completed_at_optional(self):
        task = self._task()
        self.assertIsNone(task.completed_at)


class TaskDeadlinePropertyTest(TestCase):
    def setUp(self):
        from datetime import date, timedelta
        self.today = date.today()
        self.user = User.objects.create_user(username="u", password="p")
        self.status = Status.objects.create(name="Open")
        self.done = Status.objects.create(name="Done", is_done=True)
        self.project = Project.objects.create(name="P")

    def _task(self, deadline=None, status=None):
        return Task.objects.create(
            title="T",
            project=self.project,
            assignee=self.user,
            status=status or self.status,
            deadline=deadline,
        )

    # deadline_days_remaining

    def test_days_remaining_no_deadline_returns_none(self):
        self.assertIsNone(self._task().deadline_days_remaining)

    def test_days_remaining_future(self):
        from datetime import timedelta
        task = self._task(deadline=self.today + timedelta(days=5))
        self.assertEqual(task.deadline_days_remaining, 5)

    def test_days_remaining_today(self):
        task = self._task(deadline=self.today)
        self.assertEqual(task.deadline_days_remaining, 0)

    def test_days_remaining_past(self):
        from datetime import timedelta
        task = self._task(deadline=self.today - timedelta(days=2))
        self.assertEqual(task.deadline_days_remaining, -2)

    # is_deadline_urgent

    def test_urgent_today(self):
        self.assertTrue(self._task(deadline=self.today).is_deadline_urgent)

    def test_urgent_tomorrow(self):
        from datetime import timedelta
        self.assertTrue(self._task(deadline=self.today + timedelta(days=1)).is_deadline_urgent)

    def test_urgent_past_deadline(self):
        from datetime import timedelta
        self.assertTrue(self._task(deadline=self.today - timedelta(days=1)).is_deadline_urgent)

    def test_urgent_two_days_away_is_false(self):
        from datetime import timedelta
        self.assertFalse(self._task(deadline=self.today + timedelta(days=2)).is_deadline_urgent)

    def test_urgent_no_deadline_is_false(self):
        self.assertFalse(self._task().is_deadline_urgent)

    def test_urgent_done_task_is_false(self):
        self.assertFalse(self._task(deadline=self.today, status=self.done).is_deadline_urgent)

    # is_deadline_warning

    def test_warning_two_days_away(self):
        from datetime import timedelta
        self.assertTrue(self._task(deadline=self.today + timedelta(days=2)).is_deadline_warning)

    def test_warning_three_days_away(self):
        from datetime import timedelta
        self.assertTrue(self._task(deadline=self.today + timedelta(days=3)).is_deadline_warning)

    def test_warning_one_day_away_is_false(self):
        from datetime import timedelta
        self.assertFalse(self._task(deadline=self.today + timedelta(days=1)).is_deadline_warning)

    def test_warning_four_days_away_is_false(self):
        from datetime import timedelta
        self.assertFalse(self._task(deadline=self.today + timedelta(days=4)).is_deadline_warning)

    def test_warning_no_deadline_is_false(self):
        self.assertFalse(self._task().is_deadline_warning)

    def test_warning_done_task_is_false(self):
        from datetime import timedelta
        self.assertFalse(self._task(deadline=self.today + timedelta(days=2), status=self.done).is_deadline_warning)

    def test_warning_past_deadline_is_false(self):
        from datetime import timedelta
        self.assertFalse(self._task(deadline=self.today - timedelta(days=1)).is_deadline_warning)


class TaskEventRelationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.status = Status.objects.create(name="Open")
        self.project = Project.objects.create(name="P")
        self.event = Event.objects.create(event_date="2026-06-01", project=self.project, name="Test Event")

    def _task(self, event=None):
        return Task.objects.create(
            title="T", project=self.project, assignee=self.user,
            status=self.status, event=event,
        )

    def test_event_is_optional(self):
        self.assertIsNone(self._task().event)

    def test_event_link(self):
        task = self._task(event=self.event)
        self.assertEqual(task.event, self.event)

    def test_event_reverse_accessor_returns_linked_task(self):
        task = self._task(event=self.event)
        self.assertIn(task, self.event.tasks.all())

    def test_event_reverse_accessor_excludes_unlinked_task(self):
        self.assertNotIn(self._task(), self.event.tasks.all())

    def test_event_delete_nullifies_task_event(self):
        task = self._task(event=self.event)
        self.event.delete()
        task.refresh_from_db()
        self.assertIsNone(task.event)


class RuleModelTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Proj")

    def test_str(self):
        rule = Rule.objects.create(project=self.project, name="R", pattern=".", dsl_template="")
        self.assertEqual(str(rule), "Proj: R")

    def test_enabled_default_true(self):
        rule = Rule.objects.create(project=self.project, name="R", pattern=".", dsl_template="")
        self.assertTrue(rule.enabled)


# ---------------------------------------------------------------------------
# DSL — parse
# ---------------------------------------------------------------------------

class DSLParseTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="u", password="p")
        status = Status.objects.create(name="Open")
        project = Project.objects.create(name="P")
        self.src = Task.objects.create(title="Src", project=project, assignee=user, status=status)
        self.dst = Task.objects.create(title="Dst", project=project, assignee=user, status=status)

    def test_single_link(self):
        ast = parse_dsl(f"LINK {self.src.id} -> {self.dst.id}")
        self.assertEqual(ast, [("link", self.src.id, self.dst.id)])

    def test_multiple_links(self):
        text = f"LINK {self.src.id} -> {self.dst.id}\nLINK {self.dst.id} -> {self.src.id}"
        self.assertEqual(len(parse_dsl(text)), 2)

    def test_empty_text(self):
        self.assertEqual(parse_dsl(""), [])

    def test_no_link_command(self):
        self.assertEqual(parse_dsl("no commands here"), [])

    def test_case_insensitive(self):
        ast = parse_dsl(f"link {self.src.id} -> {self.dst.id}")
        self.assertEqual(len(ast), 1)
        self.assertEqual(ast[0][0], "link")

    def test_extra_whitespace_between_tokens(self):
        ast = parse_dsl(f"LINK  {self.src.id}  ->  {self.dst.id}")
        self.assertEqual(len(ast), 1)

    def test_non_link_lines_are_ignored(self):
        text = f"# comment\nLINK {self.src.id} -> {self.dst.id}\nnot a command"
        self.assertEqual(len(parse_dsl(text)), 1)

    def test_returns_correct_ids(self):
        ast = parse_dsl(f"LINK {self.src.id} -> {self.dst.id}")
        self.assertEqual(ast[0][1], self.src.id)
        self.assertEqual(ast[0][2], self.dst.id)


# ---------------------------------------------------------------------------
# DSL — LARK grammar (future commands: TAG / PARENT / ASSIGN)
# ---------------------------------------------------------------------------

class DSLGrammarTest(TestCase):
    """Parse-only tests for the Cypher-inspired grammar extensions."""

    def setUp(self):
        user = User.objects.create_user(username="u", password="p")
        status = Status.objects.create(name="Open")
        project = Project.objects.create(name="P")
        self.t1 = Task.objects.create(title="T1", project=project, assignee=user, status=status)
        self.t2 = Task.objects.create(title="T2", project=project, assignee=user, status=status)

    # TAG ----------------------------------------------------------------

    def test_tag_bare_name(self):
        ast = parse_dsl(f"TAG {self.t1.id} urgent")
        self.assertEqual(ast, [("tag", self.t1.id, "urgent")])

    def test_tag_quoted_string(self):
        ast = parse_dsl(f'TAG {self.t1.id} "high priority"')
        self.assertEqual(ast, [("tag", self.t1.id, "high priority")])

    def test_tag_case_insensitive(self):
        ast = parse_dsl(f"tag {self.t1.id} important")
        self.assertEqual(ast[0][0], "tag")

    # PARENT -------------------------------------------------------------

    def test_parent_basic(self):
        ast = parse_dsl(f"PARENT {self.t1.id} -> {self.t2.id}")
        self.assertEqual(ast, [("parent", self.t1.id, self.t2.id)])

    def test_parent_case_insensitive(self):
        ast = parse_dsl(f"parent {self.t1.id} -> {self.t2.id}")
        self.assertEqual(ast[0][0], "parent")

    # ASSIGN -------------------------------------------------------------

    def test_assign_bare_username(self):
        ast = parse_dsl(f"ASSIGN {self.t1.id} TO alice")
        self.assertEqual(ast, [("assign", self.t1.id, "alice")])

    def test_assign_quoted_username(self):
        ast = parse_dsl(f'ASSIGN {self.t1.id} TO "alice smith"')
        self.assertEqual(ast, [("assign", self.t1.id, "alice smith")])

    def test_assign_case_insensitive(self):
        ast = parse_dsl(f"assign {self.t1.id} to bob")
        self.assertEqual(ast[0][0], "assign")

    # Mixed --------------------------------------------------------------

    def test_mixed_commands_in_one_dsl(self):
        text = (
            f"LINK {self.t1.id} -> {self.t2.id}\n"
            f"TAG {self.t1.id} urgent\n"
            f"PARENT {self.t1.id} -> {self.t2.id}\n"
            f"ASSIGN {self.t1.id} TO alice"
        )
        ast = parse_dsl(text)
        self.assertEqual(len(ast), 4)
        self.assertEqual(ast[0][0], "link")
        self.assertEqual(ast[1][0], "tag")
        self.assertEqual(ast[2][0], "parent")
        self.assertEqual(ast[3][0], "assign")

    def test_unknown_commands_ignored_mixed(self):
        text = f"LINK {self.t1.id} -> {self.t2.id}\nnot a command\nTAG {self.t1.id} foo"
        ast = parse_dsl(text)
        self.assertEqual(len(ast), 2)


# ---------------------------------------------------------------------------
# DSL — execute
# ---------------------------------------------------------------------------

class DSLExecuteTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.status = Status.objects.create(name="Open")
        self.project = Project.objects.create(name="P")
        self.src = Task.objects.create(title="Src", project=self.project, assignee=self.user, status=self.status)
        self.dst = Task.objects.create(title="Dst", project=self.project, assignee=self.user, status=self.status)

    def test_creates_relation(self):
        execute_dsl(f"LINK {self.src.id} -> {self.dst.id}")
        self.assertIn(self.dst, self.src.related_tasks.all())

    def test_nonexistent_task_does_not_raise(self):
        execute_dsl("LINK 99999 -> 99998")

    def test_idempotent(self):
        execute_dsl(f"LINK {self.src.id} -> {self.dst.id}")
        execute_dsl(f"LINK {self.src.id} -> {self.dst.id}")
        self.assertEqual(self.src.related_tasks.filter(pk=self.dst.pk).count(), 1)

    def test_execute_link_directly(self):
        execute_link(self.src.id, self.dst.id)
        self.assertIn(self.dst, self.src.related_tasks.all())

    def test_execute_link_nonexistent_src_does_not_raise(self):
        execute_link(99999, self.dst.id)

    def test_execute_link_nonexistent_dst_does_not_raise(self):
        execute_link(self.src.id, 99999)

    def test_execute_link_both_nonexistent_does_not_raise(self):
        execute_link(99999, 99998)

    def test_multiple_links_in_one_dsl(self):
        third = Task.objects.create(title="Third", project=self.project, assignee=self.user, status=self.status)
        execute_dsl(f"LINK {self.src.id} -> {self.dst.id}\nLINK {self.src.id} -> {third.id}")
        self.assertIn(self.dst, self.src.related_tasks.all())
        self.assertIn(third, self.src.related_tasks.all())


# ---------------------------------------------------------------------------
# DSL — execute ASSIGN
# ---------------------------------------------------------------------------

class DSLExecuteAssignTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="p")
        self.other = User.objects.create_user(username="bob", password="p")
        self.status = Status.objects.create(name="Open")
        self.project = Project.objects.create(name="P")
        self.task = Task.objects.create(
            title="T", project=self.project, assignee=self.user, status=self.status
        )

    def test_assign_changes_assignee(self):
        execute_dsl(f"ASSIGN {self.task.id} TO bob")
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.other)

    def test_assign_quoted_username(self):
        execute_dsl(f'ASSIGN {self.task.id} TO "bob"')
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.other)

    def test_assign_nonexistent_task_does_not_raise(self):
        execute_dsl("ASSIGN 99999 TO bob")

    def test_assign_nonexistent_user_does_not_raise(self):
        execute_dsl(f"ASSIGN {self.task.id} TO nobody")
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.user)

    def test_execute_assign_directly(self):
        execute_assign(self.task.id, "bob")
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.other)


# ---------------------------------------------------------------------------
# DSL — EVENT コマンド（パース）
# ---------------------------------------------------------------------------

class DSLEventParseTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="u", password="p")
        status = Status.objects.create(name="Open")
        project = Project.objects.create(name="P")
        self.task = Task.objects.create(title="T", project=project, assignee=user, status=status)
        self.event = Event.objects.create(event_date="2026-06-01", project=project)

    def test_event_parsed(self):
        ast = parse_dsl(f"EVENT {self.task.id} {self.event.id}")
        self.assertEqual(ast, [("event", self.task.id, self.event.id)])

    def test_event_case_insensitive(self):
        ast = parse_dsl(f"event {self.task.id} {self.event.id}")
        self.assertEqual(ast[0][0], "event")

    def test_event_mixed_with_other_commands(self):
        other_task = Task.objects.create(
            title="T2", project=self.task.project, assignee=self.task.assignee, status=self.task.status
        )
        text = f"LINK {self.task.id} -> {other_task.id}\nEVENT {self.task.id} {self.event.id}"
        ast = parse_dsl(text)
        self.assertEqual(len(ast), 2)
        self.assertEqual(ast[0][0], "link")
        self.assertEqual(ast[1][0], "event")

    def test_non_event_line_ignored(self):
        ast = parse_dsl("not a command")
        self.assertEqual(ast, [])


# ---------------------------------------------------------------------------
# DSL — EVENT コマンド（実行）
# ---------------------------------------------------------------------------

class DSLExecuteEventTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.status = Status.objects.create(name="Open")
        self.project = Project.objects.create(name="P")
        self.task = Task.objects.create(
            title="T", project=self.project, assignee=self.user, status=self.status
        )
        self.event = Event.objects.create(event_date="2026-06-01", project=self.project)

    def test_execute_event_links_task_to_event(self):
        execute_event(self.task.id, self.event.id)
        self.task.refresh_from_db()
        self.assertEqual(self.task.event, self.event)

    def test_execute_event_nonexistent_event_does_not_raise(self):
        execute_event(self.task.id, 99999)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.event)

    def test_execute_event_nonexistent_task_does_not_raise(self):
        execute_event(99999, self.event.id)

    def test_execute_dsl_event_links_task(self):
        execute_dsl(f"EVENT {self.task.id} {self.event.id}")
        self.task.refresh_from_db()
        self.assertEqual(self.task.event, self.event)


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

class RulesProcessTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.status = Status.objects.create(name="Open")
        self.project = Project.objects.create(name="P")
        self.task_a = Task.objects.create(title="A", project=self.project, assignee=self.user, status=self.status)
        self.task_b = Task.objects.create(title="B", project=self.project, assignee=self.user, status=self.status)

    def _rule(self, pattern, dsl_template, enabled=True):
        return Rule.objects.create(
            project=self.project, name="R",
            pattern=pattern, dsl_template=dsl_template, enabled=enabled,
        )

    def test_no_rules_no_effect(self):
        process_task_rules(self.task_a, text="relates to %d" % self.task_b.id)
        self.assertEqual(self.task_a.related_tasks.count(), 0)

    def test_pattern_no_match_no_dsl(self):
        self._rule(r"NOMATCH", f"LINK {{task_id}} -> {self.task_b.id}")
        process_task_rules(self.task_a, text="something else")
        self.assertEqual(self.task_a.related_tasks.count(), 0)

    def test_disabled_rule_is_ignored(self):
        self._rule(r"relates to (\d+)", "LINK {task_id} -> {group1}", enabled=False)
        process_task_rules(self.task_a, text="relates to %d" % self.task_b.id)
        self.assertEqual(self.task_a.related_tasks.count(), 0)

    def test_enabled_rule_with_match_links_tasks(self):
        self._rule(r"relates to (\d+)", "LINK {task_id} -> {group1}")
        process_task_rules(self.task_a, text="relates to %d" % self.task_b.id)
        self.assertIn(self.task_b, self.task_a.related_tasks.all())

    def test_uses_task_description_when_no_text_given(self):
        self._rule(r"relates to (\d+)", "LINK {task_id} -> {group1}")
        self.task_a.description = "relates to %d" % self.task_b.id
        self.task_a.save()
        process_task_rules(self.task_a)
        self.assertIn(self.task_b, self.task_a.related_tasks.all())

    def test_text_param_overrides_description(self):
        self._rule(r"relates to (\d+)", "LINK {task_id} -> {group1}")
        self.task_a.description = "no match here"
        process_task_rules(self.task_a, text="relates to %d" % self.task_b.id)
        self.assertIn(self.task_b, self.task_a.related_tasks.all())

    def test_task_id_is_substituted_in_template(self):
        self._rule(r"target (\d+)", "LINK {task_id} -> {group1}")
        process_task_rules(self.task_a, text="target %d" % self.task_b.id)
        self.assertIn(self.task_b, self.task_a.related_tasks.all())

    def test_multiple_rules_all_matching_all_executed(self):
        task_c = Task.objects.create(title="C", project=self.project, assignee=self.user, status=self.status)
        self._rule(r"alpha (\d+)", "LINK {task_id} -> {group1}")
        Rule.objects.create(
            project=self.project, name="R2",
            pattern=r"beta (\d+)", dsl_template="LINK {task_id} -> {group1}", enabled=True,
        )
        process_task_rules(self.task_a, text="alpha %d beta %d" % (self.task_b.id, task_c.id))
        self.assertIn(self.task_b, self.task_a.related_tasks.all())
        self.assertIn(task_c, self.task_a.related_tasks.all())

    def test_rule_from_different_project_not_applied(self):
        other_project = Project.objects.create(name="Other")
        Rule.objects.create(
            project=other_project, name="R",
            pattern=r"relates to (\d+)", dsl_template="LINK {task_id} -> {group1}", enabled=True,
        )
        process_task_rules(self.task_a, text="relates to %d" % self.task_b.id)
        self.assertEqual(self.task_a.related_tasks.count(), 0)


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

class SignalTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.status = Status.objects.create(name="Open")
        self.project = Project.objects.create(name="P")
        self.task_a = Task.objects.create(title="A", project=self.project, assignee=self.user, status=self.status)
        self.task_b = Task.objects.create(title="B", project=self.project, assignee=self.user, status=self.status)
        Rule.objects.create(
            project=self.project, name="R",
            pattern=r"relates to (\d+)", dsl_template="LINK {task_id} -> {group1}", enabled=True,
        )

    def test_comment_saved_triggers_rules(self):
        Comment.objects.create(
            author=self.user, task=self.task_a,
            description="relates to %d" % self.task_b.id,
        )
        self.assertIn(self.task_b, self.task_a.related_tasks.all())

    def test_comment_without_task_does_not_raise(self):
        Comment.objects.create(author=self.user, task=None, description="relates to 1")

    def test_task_saved_triggers_rules_via_description(self):
        self.task_a.description = "relates to %d" % self.task_b.id
        self.task_a.save()
        self.assertIn(self.task_b, self.task_a.related_tasks.all())

    def test_signal_exception_does_not_propagate(self):
        # Broken DSL template should not bubble up from signal
        Rule.objects.create(
            project=self.project, name="Bad",
            pattern=r"bad (\d+)", dsl_template="LINK {task_id} -> {missing_key}", enabled=True,
        )
        # This save triggers the bad rule; it must not raise
        self.task_a.description = "bad 999"
        self.task_a.save()


# ---------------------------------------------------------------------------
# ASSIGN ルール統合テスト
# ---------------------------------------------------------------------------

class AssignRuleIntegrationTest(TestCase):
    """ASSIGN DSL コマンドがルール・シグナル経由で正常に動作することを検証する。"""

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="p")
        self.bob = User.objects.create_user(username="bob", password="p")
        self.status = Status.objects.create(name="Open")
        self.project = Project.objects.create(name="P")
        self.task = Task.objects.create(
            title="T", project=self.project, assignee=self.owner, status=self.status
        )

    def _assign_rule(self, enabled=True):
        return Rule.objects.create(
            project=self.project, name="R",
            pattern=r"assign to (\w+)",
            dsl_template="ASSIGN {task_id} TO {group1}",
            enabled=enabled,
        )

    # --- process_task_rules 直接呼び出し ---

    def test_assign_rule_changes_assignee(self):
        self._assign_rule()
        process_task_rules(self.task, text="assign to bob")
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.bob)

    def test_assign_rule_no_match_preserves_assignee(self):
        self._assign_rule()
        process_task_rules(self.task, text="no match here")
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.owner)

    def test_assign_rule_disabled_preserves_assignee(self):
        self._assign_rule(enabled=False)
        process_task_rules(self.task, text="assign to bob")
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.owner)

    def test_assign_rule_nonexistent_user_preserves_assignee(self):
        self._assign_rule()
        process_task_rules(self.task, text="assign to nobody")
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.owner)

    # --- Task 保存シグナル ---

    def test_task_save_triggers_assign_rule(self):
        self._assign_rule()
        self.task.description = "assign to bob"
        self.task.save()
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.bob)

    def test_task_save_no_match_preserves_assignee(self):
        self._assign_rule()
        self.task.description = "just a description"
        self.task.save()
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.owner)

    # --- Comment 保存シグナル ---

    def test_comment_save_triggers_assign_rule(self):
        self._assign_rule()
        Comment.objects.create(
            author=self.owner, task=self.task, description="assign to bob"
        )
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.bob)

    def test_comment_save_no_match_preserves_assignee(self):
        self._assign_rule()
        Comment.objects.create(
            author=self.owner, task=self.task, description="just a comment"
        )
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.owner)


# ---------------------------------------------------------------------------
# Form
# ---------------------------------------------------------------------------

class TaskFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.status = Status.objects.create(name="Open")
        self.done = Status.objects.create(name="Done", is_done=True)
        self.project = Project.objects.create(name="P")
        self.task = Task.objects.create(
            title="Task", project=self.project, assignee=self.user, status=self.status
        )

    def _form(self, status):
        return TaskForm(
            data={"title": "T", "description": "test", "progress_summary": "",
                  "status": status.pk, "assignee": self.user.pk},
            instance=self.task,
        )

    def test_done_status_with_no_subtasks_is_valid(self):
        form = self._form(self.done)
        self.assertTrue(form.is_valid(), form.errors)

    def test_done_status_with_all_subtasks_done_is_valid(self):
        Task.objects.create(
            title="C", project=self.project, assignee=self.user, status=self.done, parent=self.task
        )
        form = self._form(self.done)
        self.assertTrue(form.is_valid(), form.errors)

    def test_done_status_with_incomplete_subtask_is_invalid(self):
        Task.objects.create(
            title="C", project=self.project, assignee=self.user, status=self.status, parent=self.task
        )
        form = self._form(self.done)
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_open_status_with_incomplete_subtask_is_valid(self):
        Task.objects.create(
            title="C", project=self.project, assignee=self.user, status=self.status, parent=self.task
        )
        form = self._form(self.status)
        self.assertTrue(form.is_valid(), form.errors)

    def test_deadline_field_is_optional(self):
        form = TaskForm(
            data={"title": "T", "description": "test", "progress_summary": "",
                  "status": self.status.pk, "deadline": "", "assignee": self.user.pk},
            instance=self.task,
        )
        self.assertTrue(form.is_valid(), form.errors)


# ---------------------------------------------------------------------------
# Form — Task-Event
# ---------------------------------------------------------------------------

class TaskFormEventTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.other = User.objects.create_user(username="other", password="p")
        self.status = Status.objects.create(name="Open")
        self.project = Project.objects.create(name="P")
        self.project.participants.add(self.user)
        self.event = Event.objects.create(
            event_date="2026-06-01", project=self.project, name="My Event"
        )
        self.task = Task.objects.create(
            title="T", project=self.project, assignee=self.user, status=self.status
        )
        other_project = Project.objects.create(name="Other")
        other_project.participants.add(self.other)
        self.other_event = Event.objects.create(
            event_date="2026-07-01", project=other_project, name="Other Event"
        )

    def _form(self, extra_data=None, user=None):
        data = {"title": "T", "description": "test", "progress_summary": "",
                "status": self.status.pk, "assignee": self.user.pk}
        if extra_data:
            data.update(extra_data)
        return TaskForm(data=data, user=user, instance=self.task)

    def test_event_field_is_present(self):
        self.assertIn("event", self._form(user=self.user).fields)

    def test_event_field_is_not_required(self):
        self.assertFalse(self._form(user=self.user).fields["event"].required)

    def test_form_valid_without_event(self):
        form = self._form(user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_event_queryset_includes_own_event(self):
        self.assertIn(self.event, self._form(user=self.user).fields["event"].queryset)

    def test_event_queryset_excludes_other_users_event(self):
        self.assertNotIn(self.other_event, self._form(user=self.user).fields["event"].queryset)

    def test_form_valid_with_event(self):
        form = self._form(extra_data={"event": self.event.pk}, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)


# ---------------------------------------------------------------------------
# Views — shared fixture
# ---------------------------------------------------------------------------

class BaseViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="owner", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")
        self.project = Project.objects.create(name="P")
        self.project.participants.add(self.user)
        # ステータスはプロジェクトに紐づける（TaskForm がプロジェクト別にフィルタするため）
        self.status = Status.objects.create(name="Open", project=self.project)
        self.done = Status.objects.create(name="Done", is_done=True, project=self.project)
        self.task = Task.objects.create(
            title="T", project=self.project, assignee=self.user, status=self.status
        )

    def login(self):
        self.client.force_login(self.user)

    def _other_project(self):
        p = Project.objects.create(name="Other")
        p.participants.add(self.other)
        return p


# ---------------------------------------------------------------------------
# Views — SignUp
# ---------------------------------------------------------------------------

class SignUpViewTest(TestCase):
    def test_get_returns_200(self):
        self.assertEqual(self.client.get(reverse("signup")).status_code, 200)

    def test_valid_post_creates_user_and_redirects(self):
        response = self.client.post(reverse("signup"), {
            "username": "newuser", "email": "n@n.com",
            "password1": "Str0ngPass!", "password2": "Str0ngPass!",
        })
        self.assertRedirects(response, reverse("project_list"))
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_invalid_post_redisplays_form(self):
        response = self.client.post(reverse("signup"), {
            "username": "u", "password1": "pass", "password2": "wrong",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="u").exists())


# ---------------------------------------------------------------------------
# Views — Project
# ---------------------------------------------------------------------------

class ProjectViewsTest(BaseViewTest):
    def test_project_list_requires_login(self):
        self.assertEqual(self.client.get(reverse("project_list")).status_code, 302)

    def test_project_list_shows_own_projects(self):
        self.login()
        response = self.client.get(reverse("project_list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.project, response.context["projects"])

    def test_project_list_hides_others_projects(self):
        other = self._other_project()
        self.login()
        self.assertNotIn(other, self.client.get(reverse("project_list")).context["projects"])

    def test_project_detail_own(self):
        self.login()
        self.assertEqual(
            self.client.get(reverse("project_detail", kwargs={"pk": self.project.pk})).status_code, 200
        )

    def test_project_detail_other_returns_404(self):
        self.login()
        other = self._other_project()
        self.assertEqual(
            self.client.get(reverse("project_detail", kwargs={"pk": other.pk})).status_code, 404
        )

    def test_project_detail_with_status_filter(self):
        self.login()
        response = self.client.get(
            reverse("project_detail", kwargs={"pk": self.project.pk}),
            {"status": self.status.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.status.pk, response.context["selected_status_list"])

    def test_project_create_adds_user_as_participant(self):
        self.login()
        self.client.post(reverse("project_create"), {"name": "New", "git_url": ""})
        new = Project.objects.get(name="New")
        self.assertIn(self.user, new.participants.all())

    def test_project_create_redirects_to_detail(self):
        self.login()
        response = self.client.post(reverse("project_create"), {"name": "New", "git_url": ""})
        new = Project.objects.get(name="New")
        self.assertRedirects(response, reverse("project_detail", kwargs={"pk": new.pk}))

    def test_project_update_own(self):
        self.login()
        self.client.post(
            reverse("project_update", kwargs={"pk": self.project.pk}), {"name": "Updated", "git_url": ""}
        )
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Updated")

    def test_project_update_other_returns_404(self):
        self.login()
        other = self._other_project()
        self.assertEqual(
            self.client.post(reverse("project_update", kwargs={"pk": other.pk}), {"name": "X", "git_url": ""}).status_code,
            404,
        )

    def test_project_delete_own(self):
        self.login()
        self.client.post(reverse("project_delete", kwargs={"pk": self.project.pk}))
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())

    def test_project_delete_other_returns_404(self):
        self.login()
        other = self._other_project()
        response = self.client.post(reverse("project_delete", kwargs={"pk": other.pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Project.objects.filter(pk=other.pk).exists())


# ---------------------------------------------------------------------------
# Views — Status
# ---------------------------------------------------------------------------

class StatusViewsTest(BaseViewTest):
    def _create_url(self):
        return reverse("status_create", kwargs={"project_pk": self.project.pk})

    def test_status_list(self):
        self.login()
        self.assertEqual(self.client.get(reverse("status_list")).status_code, 200)

    def test_status_detail(self):
        self.login()
        self.assertEqual(
            self.client.get(reverse("status_detail", kwargs={"pk": self.status.pk})).status_code, 200
        )

    def test_status_create(self):
        self.login()
        self.client.post(self._create_url(), {"name": "Review", "is_done": False})
        self.assertTrue(Status.objects.filter(name="Review").exists())

    def test_status_create_sets_project(self):
        self.login()
        self.client.post(self._create_url(), {"name": "Review", "is_done": False})
        status = Status.objects.get(name="Review")
        self.assertEqual(status.project, self.project)

    def test_status_create_redirects_to_project_detail(self):
        self.login()
        response = self.client.post(self._create_url(), {"name": "Review", "is_done": False})
        status = Status.objects.get(name="Review")
        self.assertRedirects(
            response,
            reverse("project_detail", kwargs={"pk": self.project.pk}) + "#tab-status",
        )

    def test_status_create_other_project_returns_404(self):
        other = self._other_project()
        self.login()
        response = self.client.post(
            reverse("status_create", kwargs={"project_pk": other.pk}),
            {"name": "X", "is_done": False},
        )
        self.assertEqual(response.status_code, 404)

    def test_status_update(self):
        self.login()
        self.client.post(
            reverse("status_update", kwargs={"pk": self.status.pk}), {"name": "Updated", "is_done": True}
        )
        self.status.refresh_from_db()
        self.assertEqual(self.status.name, "Updated")
        self.assertTrue(self.status.is_done)

    def test_status_update_redirects_to_project_detail(self):
        self.login()
        response = self.client.post(
            reverse("status_update", kwargs={"pk": self.status.pk}), {"name": "Updated", "is_done": False}
        )
        self.assertRedirects(
            response,
            reverse("project_detail", kwargs={"pk": self.project.pk}) + "#tab-status",
        )

    def test_status_delete(self):
        temp = Status.objects.create(name="Temp", project=self.project)
        self.login()
        self.client.post(reverse("status_delete", kwargs={"pk": temp.pk}))
        self.assertFalse(Status.objects.filter(pk=temp.pk).exists())

    def test_status_delete_redirects_to_project_detail(self):
        temp = Status.objects.create(name="Temp", project=self.project)
        self.login()
        response = self.client.post(reverse("status_delete", kwargs={"pk": temp.pk}))
        self.assertRedirects(
            response,
            reverse("project_detail", kwargs={"pk": self.project.pk}) + "#tab-status",
        )

    def test_status_list_requires_login(self):
        self.assertEqual(self.client.get(reverse("status_list")).status_code, 302)


# ---------------------------------------------------------------------------
# Views — Task
# ---------------------------------------------------------------------------

class TaskViewsTest(BaseViewTest):
    def test_task_list_requires_login(self):
        self.assertEqual(self.client.get(reverse("task_list")).status_code, 302)

    def test_task_list_returns_200(self):
        self.login()
        response = self.client.get(reverse("task_list"))
        self.assertEqual(response.status_code, 200)

    def test_task_list_contains_filter_form(self):
        self.login()
        response = self.client.get(reverse("task_list"))
        self.assertIn("filter_form", response.context)

    def test_task_detail_accessible_by_assignee(self):
        self.login()
        self.assertEqual(
            self.client.get(reverse("task_detail", kwargs={"pk": self.task.pk})).status_code, 200
        )

    def test_task_detail_accessible_by_project_participant(self):
        participant = User.objects.create_user(username="p2", password="pass")
        self.project.participants.add(participant)
        self.client.force_login(participant)
        self.assertEqual(
            self.client.get(reverse("task_detail", kwargs={"pk": self.task.pk})).status_code, 200
        )

    def test_task_detail_inaccessible_by_unrelated_user(self):
        other_project = Project.objects.create(name="Other")
        other_task = Task.objects.create(
            title="OtherT", project=other_project, assignee=self.other, status=self.status
        )
        self.login()
        self.assertEqual(
            self.client.get(reverse("task_detail", kwargs={"pk": other_task.pk})).status_code, 404
        )

    def test_task_detail_breadcrumbs_include_ancestors(self):
        child = Task.objects.create(
            title="Child", project=self.project, assignee=self.user, status=self.status, parent=self.task
        )
        self.login()
        response = self.client.get(reverse("task_detail", kwargs={"pk": child.pk}))
        parent_objects = response.context["parent_objects"]
        self.assertEqual(parent_objects[0], self.task)
        self.assertEqual(parent_objects[1], child)

    def test_task_detail_breadcrumbs_root_task(self):
        self.login()
        response = self.client.get(reverse("task_detail", kwargs={"pk": self.task.pk}))
        self.assertEqual(response.context["parent_objects"], [self.task])

    def test_task_create_with_project_param_sets_project(self):
        self.login()
        self.client.post(
            reverse("task_create") + f"?project={self.project.pk}",
            {"title": "New", "description": "test", "progress_summary": "",
             "status": self.status.pk, "assignee": self.user.pk},
        )
        task = Task.objects.get(title="New")
        self.assertEqual(task.project, self.project)

    def test_task_create_sets_assignee_to_current_user(self):
        self.login()
        self.client.post(
            reverse("task_create") + f"?project={self.project.pk}",
            {"title": "New", "description": "test", "progress_summary": "",
             "status": self.status.pk, "assignee": self.user.pk},
        )
        self.assertEqual(Task.objects.get(title="New").assignee, self.user)

    def test_task_create_with_parent_param_sets_parent(self):
        self.login()
        self.client.post(
            reverse("task_create") + f"?task={self.task.pk}",
            {"title": "Child", "description": "test", "progress_summary": "",
             "status": self.status.pk, "assignee": self.user.pk},
        )
        child = Task.objects.get(title="Child")
        self.assertEqual(child.parent, self.task)
        self.assertEqual(child.project, self.project)

    def test_task_create_done_status_sets_completed_at(self):
        self.login()
        self.client.post(
            reverse("task_create") + f"?project={self.project.pk}",
            {"title": "Done", "description": "test", "progress_summary": "",
             "status": self.done.pk, "assignee": self.user.pk},
        )
        self.assertIsNotNone(Task.objects.get(title="Done").completed_at)

    def test_task_create_open_status_leaves_completed_at_null(self):
        self.login()
        self.client.post(
            reverse("task_create") + f"?project={self.project.pk}",
            {"title": "Open", "description": "test", "progress_summary": "",
             "status": self.status.pk, "assignee": self.user.pk},
        )
        self.assertIsNone(Task.objects.get(title="Open").completed_at)

    def test_task_create_unrelated_project_param_returns_500(self):
        # Known app bug: when the project param belongs to another user, the view
        # does not set form.instance.project, causing an IntegrityError on save.
        other = self._other_project()
        self.client.raise_request_exception = False
        self.login()
        response = self.client.post(
            reverse("task_create") + f"?project={other.pk}",
            {"title": "X", "description": "test", "progress_summary": "",
             "status": self.status.pk, "assignee": self.user.pk},
        )
        self.assertEqual(response.status_code, 500)

    def test_task_update_sets_completed_at_when_done(self):
        self.login()
        self.client.post(
            reverse("task_update", kwargs={"pk": self.task.pk}),
            {"title": "T", "description": "test", "progress_summary": "",
             "status": self.done.pk, "assignee": self.user.pk},
        )
        self.task.refresh_from_db()
        self.assertIsNotNone(self.task.completed_at)

    def test_task_update_clears_completed_at_when_not_done(self):
        Task.objects.filter(pk=self.task.pk).update(completed_at=timezone.now())
        self.login()
        self.client.post(
            reverse("task_update", kwargs={"pk": self.task.pk}),
            {"title": "T", "description": "test", "progress_summary": "",
             "status": self.status.pk, "assignee": self.user.pk},
        )
        self.task.refresh_from_db()
        self.assertIsNone(self.task.completed_at)

    def test_task_delete_removes_task(self):
        self.login()
        self.client.post(reverse("task_delete", kwargs={"pk": self.task.pk}))
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())

    def test_task_watch_adds_to_watches(self):
        self.login()
        self.client.post(reverse("task_watch", kwargs={"pk": self.task.pk}))
        self.assertIn(self.task, self.user.watches.all())

    def test_task_unwatch_removes_from_watches(self):
        self.user.watches.add(self.task)
        self.login()
        self.client.post(reverse("task_unwatch", kwargs={"pk": self.task.pk}))
        self.assertNotIn(self.task, self.user.watches.all())

    def test_task_watch_unrelated_task_has_no_effect(self):
        other_project = Project.objects.create(name="Other")
        other_task = Task.objects.create(
            title="OtherT", project=other_project, assignee=self.other, status=self.status
        )
        self.login()
        self.client.post(reverse("task_watch", kwargs={"pk": other_task.pk}))
        self.assertNotIn(other_task, self.user.watches.all())

    def test_task_watch_requires_login(self):
        response = self.client.post(reverse("task_watch", kwargs={"pk": self.task.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(self.task, self.user.watches.all())


# ---------------------------------------------------------------------------
# Views — Task-Event
# ---------------------------------------------------------------------------

class TaskEventViewsTest(BaseViewTest):
    def setUp(self):
        super().setUp()
        self.event = Event.objects.create(
            event_date="2026-06-01", project=self.project, name="Test Event"
        )

    def test_task_create_with_event_sets_event(self):
        self.login()
        self.client.post(
            reverse("task_create") + f"?project={self.project.pk}",
            {"title": "New", "description": "test", "progress_summary": "",
             "status": self.status.pk, "event": self.event.pk, "assignee": self.user.pk},
        )
        self.assertEqual(Task.objects.get(title="New").event, self.event)

    def test_task_create_without_event_leaves_null(self):
        self.login()
        self.client.post(
            reverse("task_create") + f"?project={self.project.pk}",
            {"title": "New", "description": "test", "progress_summary": "",
             "status": self.status.pk, "assignee": self.user.pk},
        )
        self.assertIsNone(Task.objects.get(title="New").event)

    def test_task_update_sets_event(self):
        self.login()
        self.client.post(
            reverse("task_update", kwargs={"pk": self.task.pk}),
            {"title": "T", "description": "test", "progress_summary": "",
             "status": self.status.pk, "event": self.event.pk, "assignee": self.user.pk},
        )
        self.task.refresh_from_db()
        self.assertEqual(self.task.event, self.event)

    def test_task_update_clears_event(self):
        Task.objects.filter(pk=self.task.pk).update(event=self.event)
        self.login()
        self.client.post(
            reverse("task_update", kwargs={"pk": self.task.pk}),
            {"title": "T", "description": "test", "progress_summary": "",
             "status": self.status.pk, "event": "", "assignee": self.user.pk},
        )
        self.task.refresh_from_db()
        self.assertIsNone(self.task.event)


# ---------------------------------------------------------------------------
# Views — Comment
# ---------------------------------------------------------------------------

class CommentViewsTest(BaseViewTest):
    def setUp(self):
        super().setUp()
        self.comment = Comment.objects.create(
            author=self.user, task=self.task, description="Hello"
        )

    def test_comment_list_requires_login(self):
        self.assertEqual(self.client.get(reverse("comment_list")).status_code, 302)

    def test_comment_list_template_references_undefined_task_variable(self):
        # Known app bug: comment_list_component.html uses {{ comment.description|markdown:task.project }}
        # but comment_list view does not pass `task` in context, causing a template error.
        self.client.raise_request_exception = False
        self.login()
        response = self.client.get(reverse("comment_list"))
        self.assertEqual(response.status_code, 500)

    def test_comment_detail_accessible_by_author(self):
        self.login()
        self.assertEqual(
            self.client.get(reverse("comment_detail", kwargs={"pk": self.comment.pk})).status_code, 200
        )

    def test_comment_detail_accessible_by_participant(self):
        participant = User.objects.create_user(username="p2", password="pass")
        self.project.participants.add(participant)
        self.client.force_login(participant)
        self.assertEqual(
            self.client.get(reverse("comment_detail", kwargs={"pk": self.comment.pk})).status_code, 200
        )

    def test_comment_detail_inaccessible_by_unrelated_user(self):
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("comment_detail", kwargs={"pk": self.comment.pk})).status_code, 404
        )

    def test_comment_create_sets_author(self):
        self.login()
        self.client.post(
            reverse("comment_create"),
            {"description": "New comment", "task": self.task.pk},
        )
        comment = Comment.objects.get(description="New comment")
        self.assertEqual(comment.author, self.user)

    def test_comment_create_get_with_task_param_prefills_initial(self):
        self.login()
        response = self.client.get(reverse("comment_create") + f"?task={self.task.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial.get("task"), str(self.task.pk))

    def test_comment_update_own(self):
        self.login()
        self.client.post(
            reverse("comment_update", kwargs={"pk": self.comment.pk}),
            {"description": "Updated", "task": self.task.pk},
        )
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.description, "Updated")

    def test_comment_update_by_unrelated_user_returns_404(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("comment_update", kwargs={"pk": self.comment.pk}),
            {"description": "Hacked", "task": self.task.pk},
        )
        self.assertEqual(response.status_code, 404)

    def test_comment_delete_own(self):
        self.login()
        self.client.post(reverse("comment_delete", kwargs={"pk": self.comment.pk}))
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_comment_delete_by_unrelated_user_returns_404(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse("comment_delete", kwargs={"pk": self.comment.pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Comment.objects.filter(pk=self.comment.pk).exists())


# ---------------------------------------------------------------------------
# Status.project — モデル
# ---------------------------------------------------------------------------

class StatusProjectModelTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="P")
        self.other_project = Project.objects.create(name="Other")

    def test_status_can_be_linked_to_project(self):
        status = Status.objects.create(name="Open", project=self.project)
        self.assertEqual(status.project, self.project)

    def test_status_project_is_optional(self):
        status = Status.objects.create(name="Open")
        self.assertIsNone(status.project)

    def test_project_statuses_accessor(self):
        s1 = Status.objects.create(name="Open", project=self.project)
        s2 = Status.objects.create(name="Done", is_done=True, project=self.project)
        self.assertIn(s1, self.project.statuses.all())
        self.assertIn(s2, self.project.statuses.all())

    def test_project_statuses_excludes_other_project(self):
        Status.objects.create(name="Other Status", project=self.other_project)
        Status.objects.create(name="Mine", project=self.project)
        self.assertFalse(
            self.project.statuses.filter(name="Other Status").exists()
        )

    def test_project_statuses_active_filter(self):
        Status.objects.create(name="Open", project=self.project)
        Status.objects.create(name="Done", is_done=True, project=self.project)
        self.assertEqual(self.project.statuses.filter(is_done=False).count(), 1)

    def test_deleting_project_cascades_to_statuses(self):
        status = Status.objects.create(name="Open", project=self.project)
        pk = status.pk
        self.project.delete()
        self.assertFalse(Status.objects.filter(pk=pk).exists())


# ---------------------------------------------------------------------------
# TaskForm — ステータスのプロジェクト別フィルタ
# ---------------------------------------------------------------------------

class TaskFormStatusFilterTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.project = Project.objects.create(name="P")
        self.project.participants.add(self.user)
        self.other_project = Project.objects.create(name="Other")
        self.status = Status.objects.create(name="Open", project=self.project)
        self.other_status = Status.objects.create(name="OtherOpen", project=self.other_project)
        self.global_status = Status.objects.create(name="Global")  # project なし

    def test_status_queryset_shows_only_project_statuses(self):
        form = TaskForm(user=self.user, project=self.project)
        self.assertIn(self.status, form.fields["status"].queryset)

    def test_status_queryset_excludes_other_project_statuses(self):
        form = TaskForm(user=self.user, project=self.project)
        self.assertNotIn(self.other_status, form.fields["status"].queryset)

    def test_status_queryset_excludes_project_less_statuses(self):
        form = TaskForm(user=self.user, project=self.project)
        self.assertNotIn(self.global_status, form.fields["status"].queryset)

    def test_status_queryset_all_when_no_project(self):
        form = TaskForm(user=self.user, project=None)
        qs = form.fields["status"].queryset
        self.assertIn(self.status, qs)
        self.assertIn(self.other_status, qs)
        self.assertIn(self.global_status, qs)


# ---------------------------------------------------------------------------
# ProjectDetailView — ステータスのプロジェクト別コンテキスト
# ---------------------------------------------------------------------------

class ProjectDetailStatusContextTest(BaseViewTest):
    def setUp(self):
        super().setUp()
        self.other_project = Project.objects.create(name="Other")
        self.other_project.participants.add(self.user)
        self.other_status = Status.objects.create(name="OtherOpen", project=self.other_project)

    def test_status_list_contains_own_project_statuses(self):
        self.login()
        response = self.client.get(reverse("project_detail", kwargs={"pk": self.project.pk}))
        self.assertIn(self.status, response.context["status_list"])

    def test_status_list_excludes_other_project_statuses(self):
        self.login()
        response = self.client.get(reverse("project_detail", kwargs={"pk": self.project.pk}))
        self.assertNotIn(self.other_status, response.context["status_list"])

    def test_status_filter_uses_project_active_statuses(self):
        self.login()
        response = self.client.get(reverse("project_detail", kwargs={"pk": self.project.pk}))
        status_filter = response.context["status_filter"]
        self.assertIn(str(self.status.pk), status_filter)
        self.assertNotIn(str(self.other_status.pk), status_filter)

    def test_status_filter_excludes_done_statuses(self):
        self.login()
        response = self.client.get(reverse("project_detail", kwargs={"pk": self.project.pk}))
        status_filter = response.context["status_filter"]
        self.assertNotIn(str(self.done.pk), status_filter)


# ---------------------------------------------------------------------------
# build_gantt_data — assignee_ids / status_filter
# ---------------------------------------------------------------------------

class BuildGanttDataFilterTest(TestCase):
    def setUp(self):
        from datetime import date, timedelta
        self.user = User.objects.create_user(username="u", password="p")
        self.other = User.objects.create_user(username="other", password="p")
        self.project = Project.objects.create(name="P")
        self.status_open = Status.objects.create(name="Open", project=self.project)
        self.status_done = Status.objects.create(name="Done", is_done=True, project=self.project)
        deadline = date.today() + timedelta(days=7)
        self.task_mine = Task.objects.create(
            title="Mine", project=self.project, assignee=self.user,
            status=self.status_open, deadline=deadline,
        )
        self.task_others = Task.objects.create(
            title="Others", project=self.project, assignee=self.other,
            status=self.status_open, deadline=deadline,
        )
        self.task_done = Task.objects.create(
            title="Done", project=self.project, assignee=self.user,
            status=self.status_done, deadline=deadline,
        )

    def _titles(self, gantt):
        return [item["task"].title for item in gantt["tasks"]]

    def test_status_filter_active_excludes_done_tasks(self):
        from .views import build_gantt_data
        self.assertNotIn("Done", self._titles(build_gantt_data(self.project, status_filter="active")))

    def test_status_filter_active_includes_open_tasks(self):
        from .views import build_gantt_data
        self.assertIn("Mine", self._titles(build_gantt_data(self.project, status_filter="active")))

    def test_status_filter_done_excludes_open_tasks(self):
        from .views import build_gantt_data
        self.assertNotIn("Mine", self._titles(build_gantt_data(self.project, status_filter="done")))

    def test_status_filter_done_includes_done_tasks(self):
        from .views import build_gantt_data
        self.assertIn("Done", self._titles(build_gantt_data(self.project, status_filter="done")))

    def test_status_filter_all_includes_all_tasks(self):
        from .views import build_gantt_data
        titles = self._titles(build_gantt_data(self.project, status_filter="all"))
        self.assertIn("Mine", titles)
        self.assertIn("Done", titles)
        self.assertIn("Others", titles)

    def test_assignee_ids_filters_to_specified_user(self):
        from .views import build_gantt_data
        titles = self._titles(
            build_gantt_data(self.project, assignee_ids=[self.user.id], status_filter="all")
        )
        self.assertIn("Mine", titles)
        self.assertNotIn("Others", titles)

    def test_assignee_ids_none_shows_all_users(self):
        from .views import build_gantt_data
        titles = self._titles(
            build_gantt_data(self.project, assignee_ids=None, status_filter="all")
        )
        self.assertIn("Mine", titles)
        self.assertIn("Others", titles)

    def test_assignee_ids_multiple_users(self):
        from .views import build_gantt_data
        titles = self._titles(
            build_gantt_data(
                self.project,
                assignee_ids=[self.user.id, self.other.id],
                status_filter="all",
            )
        )
        self.assertIn("Mine", titles)
        self.assertIn("Others", titles)

    def test_assignee_and_status_filter_combined(self):
        from .views import build_gantt_data
        titles = self._titles(
            build_gantt_data(self.project, assignee_ids=[self.user.id], status_filter="active")
        )
        self.assertIn("Mine", titles)
        self.assertNotIn("Done", titles)
        self.assertNotIn("Others", titles)


# ---------------------------------------------------------------------------
# ガントフィルタ — ビューレベル（ProjectDetailView / ProjectListView）
# ---------------------------------------------------------------------------

class GanttFilterViewTest(BaseViewTest):
    def setUp(self):
        super().setUp()
        from datetime import date, timedelta
        deadline = date.today() + timedelta(days=7)
        self.other_user = User.objects.create_user(username="other2", password="pass")
        self.project.participants.add(self.other_user)
        self.other_task = Task.objects.create(
            title="OtherTask", project=self.project, assignee=self.other_user,
            status=self.status, deadline=deadline,
        )
        Task.objects.filter(pk=self.task.pk).update(deadline=deadline)
        self.done_task = Task.objects.create(
            title="DoneTask", project=self.project, assignee=self.user,
            status=self.done, deadline=deadline,
        )

    def _gantt_titles(self, response):
        return [item["task"].title for item in response.context["gantt"]["tasks"]]

    def test_gantt_default_hides_done_tasks(self):
        self.login()
        response = self.client.get(reverse("project_detail", kwargs={"pk": self.project.pk}))
        self.assertNotIn("DoneTask", self._gantt_titles(response))

    def test_gantt_default_shows_own_active_tasks(self):
        self.login()
        response = self.client.get(reverse("project_detail", kwargs={"pk": self.project.pk}))
        self.assertIn("T", self._gantt_titles(response))

    def test_gantt_default_hides_other_users_tasks(self):
        self.login()
        response = self.client.get(reverse("project_detail", kwargs={"pk": self.project.pk}))
        self.assertNotIn("OtherTask", self._gantt_titles(response))

    def test_gantt_status_all_shows_done_tasks(self):
        self.login()
        response = self.client.get(
            reverse("project_detail", kwargs={"pk": self.project.pk}),
            {"gantt_status": "all"},
        )
        self.assertIn("DoneTask", self._gantt_titles(response))

    def test_gantt_status_done_shows_only_done_tasks(self):
        self.login()
        response = self.client.get(
            reverse("project_detail", kwargs={"pk": self.project.pk}),
            {"gantt_status": "done"},
        )
        titles = self._gantt_titles(response)
        self.assertIn("DoneTask", titles)
        self.assertNotIn("T", titles)

    def test_gantt_assignees_param_filters_by_username(self):
        self.login()
        response = self.client.get(
            reverse("project_detail", kwargs={"pk": self.project.pk}),
            {"gantt_assignees": "other2", "gantt_status": "all"},
        )
        titles = self._gantt_titles(response)
        self.assertIn("OtherTask", titles)
        self.assertNotIn("T", titles)

    def test_gantt_context_contains_gantt_status(self):
        self.login()
        response = self.client.get(
            reverse("project_detail", kwargs={"pk": self.project.pk}),
            {"gantt_status": "done"},
        )
        self.assertEqual(response.context["gantt_status"], "done")

    def test_gantt_invalid_status_falls_back_to_active(self):
        self.login()
        response = self.client.get(
            reverse("project_detail", kwargs={"pk": self.project.pk}),
            {"gantt_status": "invalid_value"},
        )
        self.assertEqual(response.context["gantt_status"], "active")

    def test_gantt_context_contains_gantt_assignees(self):
        self.login()
        response = self.client.get(
            reverse("project_detail", kwargs={"pk": self.project.pk}),
            {"gantt_assignees": "other2"},
        )
        self.assertEqual(response.context["gantt_assignees"], "other2")


# ---------------------------------------------------------------------------
# Form — DSL field
# ---------------------------------------------------------------------------

class TaskFormDSLTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.project = Project.objects.create(name="P")
        self.project.participants.add(self.user)
        self.status = Status.objects.create(name="Open", project=self.project)
        self.task = Task.objects.create(
            title="T", project=self.project, assignee=self.user, status=self.status
        )

    def _form(self, dsl=""):
        return TaskForm(
            data={"title": "T", "description": "test", "progress_summary": "",
                  "status": self.status.pk, "assignee": self.user.pk, "dsl": dsl},
            user=self.user, project=self.project, instance=self.task,
        )

    def test_dsl_field_is_present(self):
        self.assertIn("dsl", self._form().fields)

    def test_dsl_field_is_not_required(self):
        self.assertFalse(self._form().fields["dsl"].required)

    def test_dsl_not_in_meta_fields(self):
        self.assertNotIn("dsl", TaskForm.Meta.fields)

    def test_form_valid_without_dsl(self):
        form = self._form()
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_valid_with_dsl(self):
        form = self._form(dsl=f"ASSIGN {self.task.pk} TO u")
        self.assertTrue(form.is_valid(), form.errors)

    def test_dsl_value_in_cleaned_data(self):
        dsl_text = f"ASSIGN {self.task.pk} TO u"
        form = self._form(dsl=dsl_text)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["dsl"], dsl_text)


# ---------------------------------------------------------------------------
# Views — DSL execution on save
# ---------------------------------------------------------------------------

class TaskDSLViewTest(BaseViewTest):
    def setUp(self):
        super().setUp()
        self.other_user = User.objects.create_user(username="other_user", password="pass")
        self.project.participants.add(self.other_user)

    def _post_update(self, extra_data=None):
        data = {"title": "T", "description": "test", "progress_summary": "",
                "status": self.status.pk, "assignee": self.user.pk}
        if extra_data:
            data.update(extra_data)
        self.login()
        return self.client.post(
            reverse("task_update", kwargs={"pk": self.task.pk}), data
        )

    def test_update_with_assign_dsl_changes_assignee(self):
        dsl = f"ASSIGN {self.task.pk} TO other_user"
        self._post_update({"dsl": dsl})
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.other_user)

    def test_update_with_multiline_dsl_executes_all_commands(self):
        second_task = Task.objects.create(
            title="T2", project=self.project, assignee=self.user, status=self.status
        )
        dsl = f"ASSIGN {self.task.pk} TO other_user\nLINK {self.task.pk} -> {second_task.pk}"
        self._post_update({"dsl": dsl})
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.other_user)
        self.assertIn(second_task, self.task.related_tasks.all())

    def test_update_with_empty_dsl_saves_normally(self):
        response = self._post_update({"dsl": ""})
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "T")

    def test_create_with_dsl_executes_after_save(self):
        dsl = f"ASSIGN {self.task.pk} TO other_user"
        self.login()
        self.client.post(
            reverse("task_create") + f"?project={self.project.pk}",
            {"title": "NewTask", "description": "test", "progress_summary": "",
             "status": self.status.pk, "assignee": self.user.pk, "dsl": dsl},
        )
        self.assertTrue(Task.objects.filter(title="NewTask").exists())
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.other_user)


# ---------------------------------------------------------------------------
# Form — CommentForm DSL field
# ---------------------------------------------------------------------------

class CommentFormDSLTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.project = Project.objects.create(name="P")
        self.status = Status.objects.create(name="Open", project=self.project)
        self.task = Task.objects.create(
            title="T", project=self.project, assignee=self.user, status=self.status
        )

    def _form(self, dsl=""):
        return CommentForm(
            data={"description": "test comment", "task": self.task.pk, "dsl": dsl},
        )

    def test_dsl_field_is_present(self):
        self.assertIn("dsl", self._form().fields)

    def test_dsl_field_is_not_required(self):
        self.assertFalse(self._form().fields["dsl"].required)

    def test_dsl_not_in_meta_fields(self):
        self.assertNotIn("dsl", CommentForm.Meta.fields)

    def test_form_valid_without_dsl(self):
        form = self._form()
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_valid_with_dsl(self):
        form = self._form(dsl=f"ASSIGN {self.task.pk} TO u")
        self.assertTrue(form.is_valid(), form.errors)

    def test_dsl_value_in_cleaned_data(self):
        dsl_text = f"ASSIGN {self.task.pk} TO u"
        form = self._form(dsl=dsl_text)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["dsl"], dsl_text)


# ---------------------------------------------------------------------------
# Views — Comment DSL execution on save
# ---------------------------------------------------------------------------

class CommentDSLViewTest(BaseViewTest):
    def setUp(self):
        super().setUp()
        self.other_user = User.objects.create_user(username="other_user", password="pass")
        self.project.participants.add(self.other_user)
        self.comment = Comment.objects.create(
            author=self.user, task=self.task, description="Hello"
        )

    def test_create_with_assign_dsl_changes_assignee(self):
        dsl = f"ASSIGN {self.task.pk} TO other_user"
        self.login()
        self.client.post(
            reverse("comment_create"),
            {"description": "New comment", "task": self.task.pk, "dsl": dsl},
        )
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.other_user)

    def test_create_with_multiline_dsl_executes_all_commands(self):
        second_task = Task.objects.create(
            title="T2", project=self.project, assignee=self.user, status=self.status
        )
        dsl = f"ASSIGN {self.task.pk} TO other_user\nLINK {self.task.pk} -> {second_task.pk}"
        self.login()
        self.client.post(
            reverse("comment_create"),
            {"description": "Multi DSL", "task": self.task.pk, "dsl": dsl},
        )
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.other_user)
        self.assertIn(second_task, self.task.related_tasks.all())

    def test_create_with_empty_dsl_saves_normally(self):
        self.login()
        response = self.client.post(
            reverse("comment_create"),
            {"description": "No DSL", "task": self.task.pk, "dsl": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Comment.objects.filter(description="No DSL").exists())

    def test_update_with_assign_dsl_changes_assignee(self):
        dsl = f"ASSIGN {self.task.pk} TO other_user"
        self.login()
        self.client.post(
            reverse("comment_update", kwargs={"pk": self.comment.pk}),
            {"description": "Updated", "task": self.task.pk, "dsl": dsl},
        )
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee, self.other_user)


# ---------------------------------------------------------------------------
# Tag — モデル
# ---------------------------------------------------------------------------

class TagModelTest(TestCase):
    def test_str(self):
        self.assertEqual(str(Tag.objects.create(name="bug")), "bug")

    def test_name_is_unique(self):
        Tag.objects.create(name="unique")
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Tag.objects.create(name="unique")

    def test_utf8_name(self):
        tag = Tag.objects.create(name="バグ修正")
        self.assertEqual(tag.name, "バグ修正")


class TaskTagModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.status = Status.objects.create(name="Open")
        self.project = Project.objects.create(name="P")
        self.task = Task.objects.create(
            title="T", project=self.project, assignee=self.user, status=self.status
        )

    def test_task_has_no_tags_by_default(self):
        self.assertEqual(self.task.tags.count(), 0)

    def test_task_can_have_tag(self):
        tag = Tag.objects.create(name="bug")
        self.task.tags.add(tag)
        self.assertIn(tag, self.task.tags.all())

    def test_task_can_have_multiple_tags(self):
        t1 = Tag.objects.create(name="bug")
        t2 = Tag.objects.create(name="urgent")
        self.task.tags.set([t1, t2])
        self.assertEqual(self.task.tags.count(), 2)

    def test_tag_reverse_accessor_returns_linked_task(self):
        tag = Tag.objects.create(name="frontend")
        self.task.tags.add(tag)
        self.assertIn(self.task, tag.tasks.all())


# ---------------------------------------------------------------------------
# Form — タグフィールド
# ---------------------------------------------------------------------------

class TaskFormTagFieldTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.project = Project.objects.create(name="P")
        self.project.participants.add(self.user)
        self.status = Status.objects.create(name="Open", project=self.project)
        self.task = Task.objects.create(
            title="T", project=self.project, assignee=self.user, status=self.status
        )

    def _form(self, tags="", instance=None):
        return TaskForm(
            data={"title": "T", "description": "test", "progress_summary": "",
                  "status": self.status.pk, "assignee": self.user.pk, "tags": tags},
            user=self.user, project=self.project,
            instance=instance or self.task,
        )

    def test_tags_field_is_present(self):
        self.assertIn("tags", self._form().fields)

    def test_tags_field_is_not_required(self):
        self.assertFalse(self._form().fields["tags"].required)

    def test_tags_not_in_meta_fields(self):
        self.assertNotIn("tags", TaskForm.Meta.fields)

    def test_form_valid_without_tags(self):
        form = self._form()
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_valid_with_single_tag(self):
        form = self._form(tags="bug")
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_valid_with_multiple_tags(self):
        form = self._form(tags="bug urgent frontend")
        self.assertTrue(form.is_valid(), form.errors)

    def test_save_creates_new_tag(self):
        form = self._form(tags="newbug")
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertTrue(Tag.objects.filter(name="newbug").exists())

    def test_save_assigns_tag_to_task(self):
        form = self._form(tags="mytag")
        self.assertTrue(form.is_valid(), form.errors)
        task = form.save()
        self.assertIn(Tag.objects.get(name="mytag"), task.tags.all())

    def test_save_assigns_multiple_tags(self):
        form = self._form(tags="alpha beta gamma")
        self.assertTrue(form.is_valid(), form.errors)
        task = form.save()
        tag_names = set(task.tags.values_list("name", flat=True))
        self.assertEqual(tag_names, {"alpha", "beta", "gamma"})

    def test_save_reuses_existing_tag(self):
        existing = Tag.objects.create(name="existing")
        form = self._form(tags="existing")
        self.assertTrue(form.is_valid(), form.errors)
        task = form.save()
        self.assertEqual(Tag.objects.filter(name="existing").count(), 1)
        self.assertIn(existing, task.tags.all())

    def test_save_clears_tags_when_field_is_empty(self):
        tag = Tag.objects.create(name="old")
        self.task.tags.add(tag)
        form = self._form(tags="")
        self.assertTrue(form.is_valid(), form.errors)
        task = form.save()
        self.assertEqual(task.tags.count(), 0)

    def test_initial_shows_existing_tags_on_edit(self):
        tag1 = Tag.objects.create(name="foo")
        tag2 = Tag.objects.create(name="bar")
        self.task.tags.set([tag1, tag2])
        form = TaskForm(user=self.user, project=self.project, instance=self.task)
        initial_tags = form.initial.get("tags", "")
        self.assertIn("foo", initial_tags)
        self.assertIn("bar", initial_tags)

    def test_save_utf8_tag(self):
        form = self._form(tags="バグ修正 重要")
        self.assertTrue(form.is_valid(), form.errors)
        task = form.save()
        tag_names = set(task.tags.values_list("name", flat=True))
        self.assertEqual(tag_names, {"バグ修正", "重要"})


# ---------------------------------------------------------------------------
# Filters — タグフィルタ
# ---------------------------------------------------------------------------

class TagFilterParseTest(TestCase):
    def test_tag_shortcut_maps_to_tags_name(self):
        parsed = parse_search_query("tag=bug")
        self.assertEqual(parsed.get("tags__name"), "bug")

    def test_tags_name_direct_key(self):
        parsed = parse_search_query("tags__name=urgent")
        self.assertEqual(parsed.get("tags__name"), "urgent")

    def test_tag_with_utf8_value(self):
        parsed = parse_search_query("tag=バグ")
        self.assertEqual(parsed.get("tags__name"), "バグ")

    def test_tag_combined_with_other_filters(self):
        parsed = parse_search_query("tag=bug status__is_done=False")
        self.assertEqual(parsed.get("tags__name"), "bug")
        self.assertIn("status__is_done", parsed)

    def test_tag_not_present_when_omitted(self):
        parsed = parse_search_query("status__is_done=False")
        self.assertNotIn("tags__name", parsed)


class TagFilterApplyTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.status = Status.objects.create(name="Open")
        self.project = Project.objects.create(name="P")
        self.bug_tag = Tag.objects.create(name="bug")
        self.urgent_tag = Tag.objects.create(name="urgent")
        self.task_with_bug = Task.objects.create(
            title="BugTask", project=self.project, assignee=self.user, status=self.status
        )
        self.task_with_bug.tags.add(self.bug_tag)
        self.task_with_urgent = Task.objects.create(
            title="UrgentTask", project=self.project, assignee=self.user, status=self.status
        )
        self.task_with_urgent.tags.add(self.urgent_tag)
        self.task_no_tags = Task.objects.create(
            title="NoTagTask", project=self.project, assignee=self.user, status=self.status
        )

    def _apply(self, raw):
        qs = Task.objects.all()
        return apply_task_filters(qs, parse_search_query(raw))

    def test_tag_filter_returns_matching_task(self):
        self.assertIn(self.task_with_bug, self._apply("tag=bug"))

    def test_tag_filter_excludes_untagged_task(self):
        self.assertNotIn(self.task_no_tags, self._apply("tag=bug"))

    def test_tag_filter_excludes_different_tag(self):
        self.assertNotIn(self.task_with_urgent, self._apply("tag=bug"))

    def test_tags_name_direct_filter(self):
        self.assertIn(self.task_with_urgent, self._apply("tags__name=urgent"))

    def test_tag_filter_nonexistent_returns_empty(self):
        self.assertFalse(self._apply("tag=nonexistent").exists())

    def test_tag_filter_utf8(self):
        jp_tag = Tag.objects.create(name="重要")
        self.task_no_tags.tags.add(jp_tag)
        self.assertIn(self.task_no_tags, self._apply("tag=重要"))


# ---------------------------------------------------------------------------
# Views — タグの保存
# ---------------------------------------------------------------------------

class TaskTagViewTest(BaseViewTest):
    def _post_create(self, extra_data=None):
        data = {"title": "NewTask", "description": "test", "progress_summary": "",
                "status": self.status.pk, "assignee": self.user.pk}
        if extra_data:
            data.update(extra_data)
        self.login()
        self.client.post(
            reverse("task_create") + f"?project={self.project.pk}", data
        )
        return Task.objects.get(title="NewTask")

    def _post_update(self, extra_data=None):
        data = {"title": "T", "description": "test", "progress_summary": "",
                "status": self.status.pk, "assignee": self.user.pk}
        if extra_data:
            data.update(extra_data)
        self.login()
        self.client.post(
            reverse("task_update", kwargs={"pk": self.task.pk}), data
        )
        self.task.refresh_from_db()
        return self.task

    def test_create_task_with_tags_assigns_tags(self):
        task = self._post_create({"tags": "bug urgent"})
        tag_names = set(task.tags.values_list("name", flat=True))
        self.assertEqual(tag_names, {"bug", "urgent"})

    def test_create_task_creates_new_tags_automatically(self):
        self._post_create({"tags": "brand-new-tag"})
        self.assertTrue(Tag.objects.filter(name="brand-new-tag").exists())

    def test_create_task_without_tags_has_no_tags(self):
        task = self._post_create()
        self.assertEqual(task.tags.count(), 0)

    def test_update_task_adds_tags(self):
        self._post_update({"tags": "frontend"})
        self.assertIn("frontend", self.task.tags.values_list("name", flat=True))

    def test_update_task_replaces_existing_tags(self):
        old_tag = Tag.objects.create(name="old")
        self.task.tags.add(old_tag)
        self._post_update({"tags": "new"})
        tag_names = set(self.task.tags.values_list("name", flat=True))
        self.assertEqual(tag_names, {"new"})

    def test_update_task_clears_tags_when_empty(self):
        tag = Tag.objects.create(name="remove-me")
        self.task.tags.add(tag)
        self._post_update({"tags": ""})
        self.assertEqual(self.task.tags.count(), 0)

    def test_update_task_with_utf8_tags(self):
        self._post_update({"tags": "バグ フロントエンド"})
        tag_names = set(self.task.tags.values_list("name", flat=True))
        self.assertEqual(tag_names, {"バグ", "フロントエンド"})


# ---------------------------------------------------------------------------
# TaskFilterMixin — ProjectListView デフォルトフィルタ
# ---------------------------------------------------------------------------

class ProjectListViewFilterTest(BaseViewTest):
    """ProjectListView のデフォルトフィルタ（assignee=me, is_done=False）を検証する。"""

    def setUp(self):
        super().setUp()
        self.other_user = User.objects.create_user(username="other2", password="pass")
        self.project.participants.add(self.other_user)
        self.other_task = Task.objects.create(
            title="OtherTask", project=self.project, assignee=self.other_user, status=self.status
        )
        self.done_task = Task.objects.create(
            title="DoneTask", project=self.project, assignee=self.user, status=self.done
        )

    def _task_titles(self, response):
        return {
            t.title
            for _, tasks, _ in response.context["tasks_by_project"]
            for t in tasks
        }

    def test_default_shows_own_open_tasks(self):
        self.login()
        response = self.client.get(reverse("project_list"))
        self.assertIn("T", self._task_titles(response))

    def test_default_hides_other_users_tasks(self):
        self.login()
        response = self.client.get(reverse("project_list"))
        self.assertNotIn("OtherTask", self._task_titles(response))

    def test_default_hides_done_tasks(self):
        self.login()
        response = self.client.get(reverse("project_list"))
        self.assertNotIn("DoneTask", self._task_titles(response))

    def test_filter_value_in_context(self):
        self.login()
        response = self.client.get(reverse("project_list"))
        self.assertIn("filter_value", response.context)

    def test_search_overrides_default_assignee(self):
        # status__is_done=False だけ指定 → assignee=me が外れ他ユーザのタスクが見える
        self.login()
        response = self.client.get(reverse("project_list"), {"search": "status__is_done=False"})
        self.assertIn("OtherTask", self._task_titles(response))

    def test_search_empty_shows_all(self):
        # search= 空文字でフィルタなし → 完了タスクも他ユーザタスクも表示
        self.login()
        response = self.client.get(reverse("project_list"), {"search": ""})
        titles = self._task_titles(response)
        self.assertIn("T", titles)
        self.assertIn("OtherTask", titles)
        self.assertIn("DoneTask", titles)

    def test_keyword_search_filters_by_title(self):
        self.login()
        response = self.client.get(
            reverse("project_list"), {"search": "OtherTask status__is_done=False"}
        )
        titles = self._task_titles(response)
        self.assertIn("OtherTask", titles)
        self.assertNotIn("T", titles)


# ---------------------------------------------------------------------------
# TaskFilterMixin — ProjectListView 最近更新・ウォッチセクション フィルタ
# ---------------------------------------------------------------------------

class ProjectListViewSectionFilterTest(BaseViewTest):
    """recently_updated / watching 各セクションのフィルタ動作を検証する。"""

    def setUp(self):
        super().setUp()
        self.done_task = Task.objects.create(
            title="DoneWatch", project=self.project, assignee=self.user, status=self.done
        )
        self.user.watches.add(self.task)
        self.user.watches.add(self.done_task)

    # --- ウォッチセクション ---

    def test_watch_default_hides_done_tasks(self):
        self.login()
        response = self.client.get(reverse("project_list"))
        watching = list(response.context["watching_tasks"])
        self.assertNotIn(self.done_task, watching)

    def test_watch_default_shows_open_tasks(self):
        self.login()
        response = self.client.get(reverse("project_list"))
        watching = list(response.context["watching_tasks"])
        self.assertIn(self.task, watching)

    def test_watch_search_empty_shows_all(self):
        self.login()
        response = self.client.get(reverse("project_list"), {"search_watch": ""})
        watching = list(response.context["watching_tasks"])
        self.assertIn(self.task, watching)
        self.assertIn(self.done_task, watching)

    def test_watch_filter_value_in_context(self):
        self.login()
        response = self.client.get(reverse("project_list"), {"search_watch": "assignee=me"})
        self.assertEqual(response.context["watch_filter_value"], "assignee=me")

    # --- 最近更新セクション ---

    def test_recent_filter_value_in_context(self):
        self.login()
        response = self.client.get(reverse("project_list"), {"search_recent": "q=test"})
        self.assertEqual(response.context["recent_filter_value"], "q=test")

    def test_recent_filter_value_uses_default_when_absent(self):
        self.login()
        response = self.client.get(reverse("project_list"))
        self.assertEqual(response.context["recent_filter_value"], "status__is_done=False")

    def test_recent_search_empty_shows_all_recent(self):
        # 空文字を渡すと完了タスクも表示される（時間フィルタは通過済み）
        from django.utils import timezone as tz
        self.done_task.updated_at = tz.now()
        self.done_task.save()
        self.login()
        response = self.client.get(reverse("project_list"), {"search_recent": ""})
        recently = list(response.context["recently_updated_tasks"])
        self.assertIn(self.done_task, recently)


# ---------------------------------------------------------------------------
# TaskFilterMixin — TaskListView デフォルトフィルタ
# ---------------------------------------------------------------------------

class TaskListViewFilterTest(BaseViewTest):
    """TaskListView のデフォルトフィルタ（is_done=False）を検証する。"""

    def setUp(self):
        super().setUp()
        self.done_task = Task.objects.create(
            title="DoneTask", project=self.project, assignee=self.user, status=self.done
        )
        self.other_open_task = Task.objects.create(
            title="OtherOpen", project=self.project, assignee=self.user, status=self.status
        )

    def _titles(self, response):
        return {t.title for t in response.context["tasks"]}

    def test_default_hides_done_tasks(self):
        self.login()
        response = self.client.get(reverse("task_list"))
        self.assertNotIn("DoneTask", self._titles(response))

    def test_default_shows_open_tasks(self):
        self.login()
        response = self.client.get(reverse("task_list"))
        self.assertIn("T", self._titles(response))

    def test_search_empty_shows_all(self):
        self.login()
        response = self.client.get(reverse("task_list"), {"search": ""})
        titles = self._titles(response)
        self.assertIn("DoneTask", titles)
        self.assertIn("T", titles)

    def test_search_filters_by_keyword(self):
        self.login()
        response = self.client.get(reverse("task_list"), {"search": "DoneTask"})
        titles = self._titles(response)
        self.assertIn("DoneTask", titles)
        self.assertNotIn("T", titles)

    def test_filter_value_reflects_search_param(self):
        self.login()
        response = self.client.get(reverse("task_list"), {"search": "assignee=me"})
        self.assertEqual(response.context["filter_value"], "assignee=me")
