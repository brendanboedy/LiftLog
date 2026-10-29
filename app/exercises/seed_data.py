"""The predefined exercises every user sees (FR-7).

To add or fix one: edit this list, then run `flask --app run seed-exercises`.
Names must be unique. Each value must come from the lists in app/models.py
(MUSCLE_GROUPS, EQUIPMENT_TYPES, MOVEMENT_TYPES, DIFFICULTIES) - a test checks this.

Don't rename an exercise here once people use it: the seed command matches
exercises by name, so a renamed one would be added as a new exercise.
"""

PREDEFINED_EXERCISES = [
    # ---- Chest ----
    {
        "name": "Barbell Bench Press",
        "muscle_group": "Chest", "equipment_type": "Barbell",
        "movement_type": "Compound", "difficulty": "Intermediate",
        "instructions": "Lie on a flat bench with your eyes under the bar. Grip slightly wider than "
                        "shoulder width, lower the bar to the middle of your chest, then press it back "
                        "up until your arms are straight. Keep your feet flat on the floor.",
    },
    {
        "name": "Incline Dumbbell Press",
        "muscle_group": "Chest", "equipment_type": "Dumbbell",
        "movement_type": "Compound", "difficulty": "Intermediate",
        "instructions": "Set a bench to about 30 degrees. Start with the dumbbells above your upper "
                        "chest, lower them until your elbows are slightly below the bench, then press "
                        "them back up.",
    },
    {
        "name": "Push-Up",
        "muscle_group": "Chest", "equipment_type": "Bodyweight",
        "movement_type": "Compound", "difficulty": "Beginner",
        "instructions": "Start in a plank with hands a little wider than your shoulders. Keep your body "
                        "in a straight line, lower your chest close to the floor, then push back up.",
    },
    {
        "name": "Cable Chest Fly",
        "muscle_group": "Chest", "equipment_type": "Cable",
        "movement_type": "Isolation", "difficulty": "Beginner",
        "instructions": "Stand between two cable pulleys set at shoulder height. With a slight bend in "
                        "your elbows, bring the handles together in front of your chest, then return slowly.",
    },
    # ---- Back ----
    {
        "name": "Deadlift",
        "muscle_group": "Back", "equipment_type": "Barbell",
        "movement_type": "Compound", "difficulty": "Advanced",
        "instructions": "Stand with the bar over the middle of your feet. Hinge at the hips, grip the "
                        "bar, flatten your back, then stand up by pushing through your legs. Keep the bar "
                        "close to your body on the way up and down.",
    },
    {
        "name": "Pull-Up",
        "muscle_group": "Back", "equipment_type": "Bodyweight",
        "movement_type": "Compound", "difficulty": "Intermediate",
        "instructions": "Hang from a bar with an overhand grip a little wider than your shoulders. Pull "
                        "until your chin is over the bar, then lower yourself all the way down with control.",
    },
    {
        "name": "Lat Pulldown",
        "muscle_group": "Back", "equipment_type": "Cable",
        "movement_type": "Compound", "difficulty": "Beginner",
        "instructions": "Sit with your thighs under the pads and grip the bar wide. Pull the bar down to "
                        "your upper chest while squeezing your shoulder blades together, then let it rise slowly.",
    },
    {
        "name": "Barbell Row",
        "muscle_group": "Back", "equipment_type": "Barbell",
        "movement_type": "Compound", "difficulty": "Intermediate",
        "instructions": "Hinge forward with a flat back and the bar hanging at arm's length. Pull the bar "
                        "to your lower ribs, pause, then lower it under control.",
    },
    {
        "name": "Seated Cable Row",
        "muscle_group": "Back", "equipment_type": "Cable",
        "movement_type": "Compound", "difficulty": "Beginner",
        "instructions": "Sit tall with your feet on the platform. Pull the handle to your stomach, "
                        "squeeze your shoulder blades together, then straighten your arms slowly.",
    },
    {
        "name": "Single-Arm Dumbbell Row",
        "muscle_group": "Back", "equipment_type": "Dumbbell",
        "movement_type": "Compound", "difficulty": "Beginner",
        "instructions": "Put one knee and hand on a bench. Pull the dumbbell toward your hip with the "
                        "other arm, keeping your back flat, then lower it. Switch sides.",
    },
    # ---- Shoulders ----
    {
        "name": "Overhead Press",
        "muscle_group": "Shoulders", "equipment_type": "Barbell",
        "movement_type": "Compound", "difficulty": "Intermediate",
        "instructions": "Stand with the bar resting on your front shoulders. Press it straight overhead "
                        "until your arms lock out, then lower it back to your shoulders. Keep your core tight.",
    },
    {
        "name": "Dumbbell Shoulder Press",
        "muscle_group": "Shoulders", "equipment_type": "Dumbbell",
        "movement_type": "Compound", "difficulty": "Beginner",
        "instructions": "Sit or stand with the dumbbells at shoulder height, palms forward. Press them "
                        "overhead, then lower them back to shoulder height.",
    },
    {
        "name": "Dumbbell Lateral Raise",
        "muscle_group": "Shoulders", "equipment_type": "Dumbbell",
        "movement_type": "Isolation", "difficulty": "Beginner",
        "instructions": "Hold the dumbbells at your sides. With a slight bend in your elbows, raise your "
                        "arms out to shoulder height, then lower them slowly.",
    },
    {
        "name": "Face Pull",
        "muscle_group": "Shoulders", "equipment_type": "Cable",
        "movement_type": "Isolation", "difficulty": "Beginner",
        "instructions": "Set a rope at upper-chest height. Pull the rope toward your face, separating "
                        "the ends and pointing your elbows out, then return slowly.",
    },
    # ---- Arms ----
    {
        "name": "Barbell Curl",
        "muscle_group": "Biceps", "equipment_type": "Barbell",
        "movement_type": "Isolation", "difficulty": "Beginner",
        "instructions": "Stand holding the bar with palms facing forward. Keep your elbows at your sides, "
                        "curl the bar to your shoulders, then lower it slowly.",
    },
    {
        "name": "Hammer Curl",
        "muscle_group": "Biceps", "equipment_type": "Dumbbell",
        "movement_type": "Isolation", "difficulty": "Beginner",
        "instructions": "Hold the dumbbells with palms facing each other. Curl them up without turning "
                        "your wrists, then lower them slowly.",
    },
    {
        "name": "Triceps Pushdown",
        "muscle_group": "Triceps", "equipment_type": "Cable",
        "movement_type": "Isolation", "difficulty": "Beginner",
        "instructions": "Stand at a high cable with a bar or rope. Keep your elbows at your sides and push "
                        "down until your arms are straight, then let the handle rise slowly.",
    },
    {
        "name": "Overhead Dumbbell Triceps Extension",
        "muscle_group": "Triceps", "equipment_type": "Dumbbell",
        "movement_type": "Isolation", "difficulty": "Beginner",
        "instructions": "Hold one dumbbell overhead with both hands. Lower it behind your head by bending "
                        "your elbows, then straighten your arms.",
    },
    {
        "name": "Bench Dip",
        "muscle_group": "Triceps", "equipment_type": "Bodyweight",
        "movement_type": "Compound", "difficulty": "Beginner",
        "instructions": "Put your hands on the edge of a bench behind you with legs out in front. Lower "
                        "your body by bending your elbows, then push back up.",
    },
    {
        "name": "Farmer's Carry",
        "muscle_group": "Forearms", "equipment_type": "Dumbbell",
        "movement_type": "Compound", "difficulty": "Beginner",
        "instructions": "Hold a heavy dumbbell in each hand at your sides. Stand tall and walk for a set "
                        "distance or time without letting your shoulders slump.",
    },
    # ---- Legs ----
    {
        "name": "Barbell Back Squat",
        "muscle_group": "Quadriceps", "equipment_type": "Barbell",
        "movement_type": "Compound", "difficulty": "Intermediate",
        "instructions": "Rest the bar on your upper back. With feet about shoulder width apart, sit down "
                        "and back until your thighs are at least parallel to the floor, then stand back up. "
                        "Keep your chest up and knees in line with your toes.",
    },
    {
        "name": "Goblet Squat",
        "muscle_group": "Quadriceps", "equipment_type": "Dumbbell",
        "movement_type": "Compound", "difficulty": "Beginner",
        "instructions": "Hold a dumbbell upright against your chest. Squat down between your knees while "
                        "keeping your chest up, then stand back up.",
    },
    {
        "name": "Leg Press",
        "muscle_group": "Quadriceps", "equipment_type": "Machine",
        "movement_type": "Compound", "difficulty": "Beginner",
        "instructions": "Sit in the machine with your feet shoulder width apart on the platform. Lower the "
                        "platform until your knees are bent about 90 degrees, then push it back up without "
                        "locking your knees.",
    },
    {
        "name": "Leg Extension",
        "muscle_group": "Quadriceps", "equipment_type": "Machine",
        "movement_type": "Isolation", "difficulty": "Beginner",
        "instructions": "Sit with the pad on the front of your ankles. Straighten your legs, pause, then "
                        "lower the weight slowly.",
    },
    {
        "name": "Walking Lunge",
        "muscle_group": "Quadriceps", "equipment_type": "Bodyweight",
        "movement_type": "Compound", "difficulty": "Beginner",
        "instructions": "Step forward and lower until both knees are bent about 90 degrees. Push through "
                        "the front foot and step into the next lunge with the other leg.",
    },
    {
        "name": "Romanian Deadlift",
        "muscle_group": "Hamstrings", "equipment_type": "Barbell",
        "movement_type": "Compound", "difficulty": "Intermediate",
        "instructions": "Hold the bar at your hips. With a slight knee bend, push your hips back and lower "
                        "the bar along your legs until you feel a stretch in your hamstrings, then stand up.",
    },
    {
        "name": "Lying Leg Curl",
        "muscle_group": "Hamstrings", "equipment_type": "Machine",
        "movement_type": "Isolation", "difficulty": "Beginner",
        "instructions": "Lie face down with the pad behind your ankles. Curl your heels toward your glutes, "
                        "then lower slowly.",
    },
    {
        "name": "Barbell Hip Thrust",
        "muscle_group": "Glutes", "equipment_type": "Barbell",
        "movement_type": "Compound", "difficulty": "Intermediate",
        "instructions": "Sit with your upper back against a bench and the bar across your hips. Drive your "
                        "hips up until your body is straight from shoulders to knees, squeeze, then lower.",
    },
    {
        "name": "Standing Calf Raise",
        "muscle_group": "Calves", "equipment_type": "Machine",
        "movement_type": "Isolation", "difficulty": "Beginner",
        "instructions": "Stand with the balls of your feet on the platform. Rise onto your toes as high as "
                        "you can, pause, then lower your heels below the platform.",
    },
    # ---- Core ----
    {
        "name": "Plank",
        "muscle_group": "Core", "equipment_type": "Bodyweight",
        "movement_type": "Isolation", "difficulty": "Beginner",
        "instructions": "Rest on your forearms and toes with your body in a straight line. Hold the "
                        "position without letting your hips sag.",
    },
    {
        "name": "Hanging Leg Raise",
        "muscle_group": "Core", "equipment_type": "Bodyweight",
        "movement_type": "Isolation", "difficulty": "Intermediate",
        "instructions": "Hang from a bar. Keeping your legs straight, raise them to hip height or higher, "
                        "then lower them slowly without swinging.",
    },
    {
        "name": "Cable Crunch",
        "muscle_group": "Core", "equipment_type": "Cable",
        "movement_type": "Isolation", "difficulty": "Beginner",
        "instructions": "Kneel under a high cable holding a rope by your head. Curl your chest toward your "
                        "knees using your abs, then return slowly.",
    },
    # ---- Full body ----
    {
        "name": "Kettlebell Swing",
        "muscle_group": "Full Body", "equipment_type": "Kettlebell",
        "movement_type": "Compound", "difficulty": "Intermediate",
        "instructions": "Stand with feet wide and the kettlebell in both hands. Hinge at the hips, then "
                        "snap your hips forward to swing the kettlebell to chest height. Let it swing back "
                        "between your legs and repeat.",
    },
    {
        "name": "Band Pull-Apart",
        "muscle_group": "Shoulders", "equipment_type": "Resistance Band",
        "movement_type": "Isolation", "difficulty": "Beginner",
        "instructions": "Hold a band in front of you at shoulder height with straight arms. Pull it apart "
                        "until it touches your chest, then return slowly.",
    },
]
