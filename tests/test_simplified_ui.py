"""Checks for direct workout starts and private previous-set suggestions."""
from datetime import date

from app.extensions import db
from app.models import User, Exercise, WorkoutTemplate, WorkoutTemplateExercise, WorkoutSession, WorkoutSessionExercise, SetEntry


def sign_in(client, user):
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True


def test_home_lists_only_owned_routines_and_prioritizes_active_workout(client, app):
    user = User(username='me', password_hash='unused')
    other = User(username='other', password_hash='unused')
    db.session.add_all([user, other]); db.session.flush()
    db.session.add_all([
        WorkoutTemplate(user_id=user.id, name='My routine', difficulty='Beginner'),
        WorkoutTemplate(user_id=other.id, name='Private routine', difficulty='Beginner'),
        WorkoutSession(user_id=user.id, name='Current workout'),
    ])
    db.session.commit(); sign_in(client, user)
    page = client.get('/dashboard')
    assert page.status_code == 200
    assert b'My routine' in page.data and b'Private routine' not in page.data
    assert b'Continue workout' in page.data
    assert b'Start workout</button>' not in page.data


def test_previous_set_uses_only_own_completed_history(client, app):
    user = User(username='me', password_hash='unused')
    other = User(username='other', password_hash='unused')
    exercise = Exercise(name='Squat', muscle_group='Quadriceps', equipment_type='Barbell', movement_type='Compound', difficulty='Beginner')
    db.session.add_all([user, other, exercise]); db.session.flush()
    for owner, weight in [(user, 50), (other, 999)]:
        past = WorkoutSession(user_id=owner.id, name='Past', completed=True, date_performed=date.today())
        item = WorkoutSessionExercise(exercise_id=exercise.id, order_index=1)
        item.sets.append(SetEntry(set_number=1, weight=weight, reps=10))
        past.items.append(item); db.session.add(past)
    active = WorkoutSession(user_id=user.id, name='Today')
    item = WorkoutSessionExercise(exercise_id=exercise.id, order_index=1)
    active.items.append(item); db.session.add(active); db.session.commit()
    sign_in(client, user)
    page = client.get(f'/sessions/{active.id}')
    assert page.status_code == 200
    assert 'Last time: 50 lb × 10 reps'.encode() in page.data
    assert b'999' not in page.data
    assert b'value="50.0"' in page.data
    item.sets.append(SetEntry(set_number=1, weight=60, reps=8)); db.session.commit()
    page = client.get(f'/sessions/{active.id}')
    assert b'value="60.0"' in page.data


def test_routine_management_is_an_explicit_view(client, app):
    user = User(username='me', password_hash='unused')
    exercise = Exercise(name='Squat', muscle_group='Quadriceps', equipment_type='Barbell', movement_type='Compound', difficulty='Beginner')
    db.session.add_all([user, exercise]); db.session.flush()
    routine = WorkoutTemplate(user_id=user.id, name='Leg day', difficulty='Beginner')
    routine.items.append(WorkoutTemplateExercise(exercise_id=exercise.id, order_index=1, target_sets=3, rep_range_min=8, rep_range_max=12))
    db.session.add(routine); db.session.commit(); sign_in(client, user)
    page = client.get(f'/templates/{routine.id}')
    assert b'Start this workout' in page.data and b'Edit routine' in page.data
    assert b'Make public' not in page.data and b'Add an exercise' not in page.data
    edit = client.get(f'/templates/{routine.id}?manage=1')
    assert b'Make public' in edit.data and b'Add an exercise' in edit.data
