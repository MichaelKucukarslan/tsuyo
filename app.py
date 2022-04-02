from crypt import methods
import imp
from unicodedata import name
from flask import Flask, redirect, render_template, request, session
from werkzeug.security import generate_password_hash

from helper import message, get_db_connection

from user import User
from head_set import Head_set
from workout import Workout
from ex_set import Ex_set
from exercise import Exercise
from graph_set import Graph_set

app = Flask(__name__)
app.secret_key = "toots"

# Setup databases from all classes
database = get_db_connection()
User.db = database
Workout.db = database
Ex_set.db = database
Exercise.db = database

@app.route('/')
def index():
   session.clear()
   return render_template("login.html")

@app.route('/login', methods=["GET", "POST"])
def login():
   user = User.get("fun@gmail.com")
   session['userID'] = user.get_id()
   session['name'] = user.get_first_name()
   session['email'] = user.get_email()
   return redirect("/user_index")
   # remove any prior session
   session.clear()
   if request.method == "POST":
      # check that a user name was submitted
      if not request.form.get("email"):
         # return a page stating no user name
         return message("Need an e-mail")

      # check that a password was submitted
      if not request.form.get("password"):
         # return a page stating no password
         return message("Need a password")

      # Get user if one exists
      email = request.form.get("email")
      user = User.get(email)

      if not user: # If user does not exist send user error message
         return message("Invalid credentials")
      
      # Check passwork and send to user_index if correct
      password = request.form.get('password')
      if user.check_password(password):
         session['userID'] = user.get_id()
         session['name'] = user.get_first_name()
         session['email'] = user.get_email()
         return redirect("/user_index")
      # If password did not match give user error message
      return message("Invalid credentials")

@app.route('/graph', methods=["GET"])
def graph():
   if not session.get('userID'):
      return message("Must be logged in.")
   
   
   cur = database.cursor()
   u_id = session['userID']
   # get the exercises the user has done
   query = """SELECT users.firstName, workouts.dateandtime AS w_datetime, workouts.id AS w_id, sets.id AS s_id, sets.interval AS s_interval, sets.resistance AS s_res,
      sets.setNumber AS s_setNum, sets.workoutID AS s_workID, sets.exerciseID AS s_exeID, exercises.name AS e_name FROM users
      JOIN workouts ON users.id = workouts.userID JOIN sets ON workouts.id = sets.workoutID JOIN exercises ON
      sets.exerciseID = exercises.id WHERE users.id = ? ORDER BY exercises.id"""
   exercises = cur.execute(query, [u_id]).fetchall()
   graph_exercises = []
   for i in exercises:
      graph_exercises.append(Graph_set(i['s_id'], i['s_interval'], i['s_res'], i['s_setNum'], i['w_id'], i['w_datetime'], i['s_exeID'], i['e_name']))
      
   # find the first exercise of the exercises
   exercise_id = graph_exercises[0].exercise_id
   # start a small list
   big_lst = []
   small_lst = []
   for i in graph_exercises:
      # add to small list til exercise changes
      if i.exercise_id == exercise_id:
         small_lst.append(i)
      else:
         # add small list to big list
         big_lst.append(small_lst)
         # start a new small list
         small_lst = []
         exercise_id = i.exercise_id
         small_lst.append(i)

   for i in big_lst:
      for j in i:
         print(j.exercise_name, sep=' ')
      print()
   print(len(big_lst))
   # pass graph data to html page
   return render_template("graph.html", graph_exercises=graph_exercises)

@app.route('/begin_edit_set', methods=["POST"])
def begin_edit_set():
   set_id = request.form.get('edit-set')
   cur = User.db.cursor()
   s_id = []
   s_id.append(set_id)
   query = """SELECT users.firstName, workouts.dateandtime AS w_datetime, workouts.id as w_id, sets.id AS s_id, sets.interval AS s_interval, sets.resistance AS s_res,
      sets.setNumber AS s_setNum, sets.workoutID AS s_workID, sets.exerciseID AS s_exeID, exercises.name AS e_name FROM users
      JOIN workouts ON users.id = workouts.userID JOIN sets ON workouts.id = sets.workoutID JOIN exercises ON
      sets.exerciseID = exercises.id WHERE s_id = ?"""
   set_to_edit = cur.execute(query, s_id).fetchone()
   return render_template("edit_set.html", set_to_edit=set_to_edit)

@app.route('/edit_set', methods=["POST"])
def edit_set():
   set_id = request.form.get('edit-set')
   
   # Get workout id, create a workout if one does not exist
   datetime = request.form.get('datetime')
   workout_id =  Workout.get_workout_id(datetime, session['userID'])
   if workout_id:
      workout_id = workout_id[0]
   else:
      Workout.create_workout(datetime, session['userID'])
      workout_id = Workout.get_workout_id(datetime, session['userID'])[0]
   
   # Get exercise id, create one if one does not exist
   name = request.form.get('e_name')
   exercise_id = Exercise.get_exercise_id(name)
   if exercise_id:
      exercise_id = exercise_id[0]
   else:
      Exercise.create_exercise(name)
      exercise_id = Exercise.get_exercise_id(name)[0]

   interval = request.form.get('s_interval')
   resistance = request.form.get('s_res')
   query = """UPDATE sets SET interval=?, resistance=?, workoutID=?, exerciseID=? WHERE ID=?"""
   # edit the set
   database.execute(query, [interval, resistance, workout_id, exercise_id, set_id])
   database.commit()
   return message("Set edited successfully")

@app.route('/user_index')
# @login_required
def user_index():
   if not session.get('userID'):
      return message("Must be logged in.")

   cur = User.db.cursor()
   userID = []
   userID.append(session['userID']) # needs to be in a list to use .execute
   query = """SELECT users.firstName, workouts.dateandtime AS w_datetime, workouts.id as w_id, sets.id AS s_id, sets.interval AS s_interval, sets.resistance AS s_res,
      sets.setNumber AS s_setNum, sets.workoutID AS s_workID, sets.exerciseID AS s_exeID, exercises.name AS e_name FROM users
      JOIN workouts ON users.id = workouts.userID JOIN sets ON workouts.id = sets.workoutID JOIN exercises ON
      sets.exerciseID = exercises.id WHERE users.id = ? ORDER BY w_id DESC"""
   exercises = cur.execute(query, userID).fetchall()

   # If there are zero exercises show the user there name
   if not exercises:
      return render_template("index.html", name=session['name'])

   # Get all the exercises in head_set class
   head_sets = []
   for ex in exercises:
      # make a head_set form all the exercises
      head_set = Head_set(Workout.get(ex['w_id']), Exercise.get(ex['s_exeID']), Ex_set.get(ex['s_id']))
      head_sets.append(head_set)
   
   all_workout_dates = [hs.get_workout().get_date_time() for hs in head_sets]
   workout_date_dict = {d: {} for d in all_workout_dates}

   number_of_columns_for_table = 0
   for hs in head_sets:
      date = hs.get_workout().get_date_time()
      name = hs.get_exercise().get_name()
      interval = hs.get_ex_set().interval
      resistance = hs.get_ex_set().resistance
      set_id = hs.get_ex_set().id
      if name in workout_date_dict[date]:
         workout_date_dict[date][name] += [interval, resistance, set_id]
      else:
         workout_date_dict[date][name] = [interval, resistance, set_id]
      curr_columns = len(workout_date_dict[date][name])
      if curr_columns > number_of_columns_for_table:
         number_of_columns_for_table = curr_columns
   number_of_columns_for_table = int(number_of_columns_for_table / 3)

   single_workout_dates = sorted(workout_date_dict.keys(), reverse=True)
   return render_template("index.html", dates=single_workout_dates, workouts=workout_date_dict, columns=number_of_columns_for_table) 

@app.route('/exercise', methods=["GET", "POST"])
def exercise():
   if not session.get('userID'):
      return message("Need to be logged in")
   if request.method == "POST":
      dates = request.form.getlist("ndatetime[]")
      exercises = request.form.getlist("nExercise[]")
      set_numbers = request.form.getlist("nsetnumber[]")
      repetitions = request.form.getlist("nrep[]")
      resistances = request.form.getlist("nresistance[]")
      zippedExercises = zip(dates, exercises, set_numbers, repetitions, resistances)
      for exercises in zippedExercises:
         # Create workout day and time if one does not exist
         doesWorkoutExist = Workout.get_workout_id(exercises[0], session['userID'])
         workoutID = -1
         if doesWorkoutExist is None:
            # Add a T to the datetime
            date_time_str = ''
            for i, v in enumerate(exercises[0]):
               if i == 10:
                  date_time_str += 'T'
               else:
                  date_time_str += v
            Workout.create_workout(date_time_str, session['userID'])
            workoutID = Workout.get_workout_id(date_time_str, session['userID'])[0]
         else:
            workoutID = doesWorkoutExist[0]
         
         # Create exercise if one does not exist
         word = ''.join(exercises[1])
         doesExerciseExist = Exercise.get_exercise_id(word)
         exerciseID = -1
         if doesExerciseExist is None:
            Exercise.create_exercise(word)
            exerciseID = Exercise.get_exercise_id(word)[0]
         else:
            exerciseID = doesExerciseExist[0]
      
         # Create the set
         sql = "INSERT INTO sets (workoutID, exerciseID, setNumber, interval, resistance) VALUES (?, ?, ?, ?, ?)"
         database.execute(sql, [workoutID, exerciseID, exercises[2], exercises[3], exercises[4]])
         database.commit()
   return render_template("exercise.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
   if request.method == "GET":
      return render_template("register.html")

   if request.method == "POST":
   # Check First Name text box 
      first_name = request.form.get("first_name")
      if not first_name:
         return message("Need to input a first name.")
   # Check Last Name text box 
      last_name = request.form.get("last_name")
      if not last_name:
         return message("Need to input a last name.")
   # Check E-Mail text box 
      email_address = request.form.get("email_address")
      if not email_address:
         return message("Need to input an e-mail address.")
   # Check Date of Birth text box 
      date_of_birth = request.form.get("date_of_birth")
      if not date_of_birth:
         return message("Need to input a date of birth.")
   # Check Password text box 
      password = request.form.get("password")
      if not password:
         return message("Need to input a password.")
   # Check Confirm Password text box 
      confirm_password = request.form.get("confirm_password")
      if not confirm_password:
         return message("Need to input a confermation password.")

      # Check if passwords match
      if password != confirm_password:
         return message("Password and Confirm Password does not match")
      
      # Check for existing user with email address
      if User.get(email_address):
         return message("E-mail already in use")
      # Create the new user
      ls = [last_name, first_name, email_address, date_of_birth, generate_password_hash(password)]
      User.add_user(ls)
   return message("You successfully registered. Go ahead and log in on the log in page.")

@app.route('/settings', methods=['GET', 'POST'])
def settings():
   if not session.get('userID'):
      return message("Must be logged in.")

   if request.method == "GET":
      return render_template("settings.html")

   if request.method == "POST":
      user = User.get(session["email"])
      ls = {}
      ls['email'] = request.form.get("email")
      ls['last_name'] = request.form.get("last-name")
      ls['first_name'] = request.form.get("first_name")
      ls['date_of_birth'] = request.form.get("date-of-birth")
      ls['change_password'] = request.form.get("change-password")
      ls['confirm_password'] = request.form.get("confirm-password")
      ls['original_password'] = request.form.get("original-password")

      # Test the original password
      if user.change_user_data(ls) == 1:
         return message("Need correct original password")
      elif user.change_user_data(ls) == 2:
         return message("Changed passwords do not match")
      
      user = User.get(session['email'])
      session['name'] = user.get_first_name()
      return message("Successfully changed your settings")

    
@app.route('/logout')
def logout():
   session.clear()
   return message("Logged Out")

if __name__ == '__main__':
   app.run()