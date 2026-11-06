# Improvements for V2 of ISAT Recruiter


# course Planner improvements
1. Better prerequisite course handling for the schedule planner, as well as including pass courses as completed courses that will not be included in a newly generated schedule

2. Allow users to be able to change different classes and make adjustments to their schedule, as in following up after the schedule is generated and regenerating a schedule based on that feedback the user gives.


# HOW : intake workflow 
1.  ask the user what year standing they are and how many credit hours they have. It's like, "What year standing are you?"
    freshman (#-# credit hours), softmore (#-#credit hours)...
- Ask the student when they plan to graduate, with 4 years from the date that they started being on track. If they're a sophomore, they should graduate at the end of their senior year. However, ask them if they're planning to graduate on time with their year, or give them an option for next semesters or earlier semesters as well.

2. How many general education classes student taken.

3. Ask which courses. First, we're going to start with the prerequisite courses for the basic ISAt major and sort them by how they're sorted on the page. The user is going to be able to check them off or click them to establish what they have taken.
 
- This will all go in an intermediary data structure as well that will store the past courses that the student took. Then they will be compared to the prerequisites to see which courses are left over.

4. Concentration question 

5. sector question

6. Ask the user if they plan to take any courses at a specific time. They will type that out, or there's a button for just "Generate my schedule" (generic).

7. Afterwards, the user will be able to change the schedule and make modifications.


# edge cases to address
- The student may be a freshman or sophomore with zero credits in ISAT, only Gen Ed credit requirements