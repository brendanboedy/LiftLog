"""The predefined workout templates every user sees (FR-19).

To add or fix one: edit this list, then run `flask --app run seed-templates`
(after `seed-exercises`, since templates use the predefined exercises).
Each exercise is (exercise name, target sets, min reps, max reps). Exercise
names must match PREDEFINED_EXERCISES exactly - a test checks this.

Don't rename a template here once people use it: the seed command matches
templates by name, so a renamed one would be added as a new template.
"""

PREDEFINED_TEMPLATES = [
    {
        "name": "Full Body Beginner",
        "difficulty": "Beginner",
        "description": "A simple whole-body workout for your first weeks of lifting. "
                       "Do it two or three times a week with a rest day in between.",
        "exercises": [
            ("Goblet Squat", 3, 8, 12),
            ("Push-Up", 3, 8, 15),
            ("Lat Pulldown", 3, 8, 12),
            ("Dumbbell Shoulder Press", 3, 8, 12),
            ("Romanian Deadlift", 3, 8, 12),
        ],
    },
    {
        "name": "Push Day",
        "difficulty": "Intermediate",
        "description": "Chest, shoulders and triceps.",
        "exercises": [
            ("Barbell Bench Press", 4, 6, 10),
            ("Overhead Press", 3, 6, 10),
            ("Incline Dumbbell Press", 3, 8, 12),
            ("Dumbbell Lateral Raise", 3, 12, 15),
            ("Triceps Pushdown", 3, 10, 15),
        ],
    },
    {
        "name": "Pull Day",
        "difficulty": "Intermediate",
        "description": "Back and biceps.",
        "exercises": [
            ("Barbell Row", 4, 6, 10),
            ("Pull-Up", 3, 5, 10),
            ("Seated Cable Row", 3, 8, 12),
            ("Face Pull", 3, 12, 15),
            ("Hammer Curl", 3, 10, 12),
        ],
    },
    {
        "name": "Leg Day",
        "difficulty": "Intermediate",
        "description": "Quads, hamstrings, glutes and calves.",
        "exercises": [
            ("Barbell Back Squat", 4, 6, 10),
            ("Romanian Deadlift", 3, 8, 10),
            ("Leg Press", 3, 10, 12),
            ("Lying Leg Curl", 3, 10, 12),
            ("Standing Calf Raise", 4, 10, 15),
        ],
    },
]
