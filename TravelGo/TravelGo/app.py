from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = '560aedc57c1b2b8a08b50165fb3edd0576b45ed25cc14fc0a5373feb8eff05ca' # IMPORTANT: CHANGE THIS TO A REAL, STRONG, RANDOM KEY!

# MongoDB connection
client = MongoClient('mongodb+srv://228x1a4436:IOfox5usz7dOwKJ4@cluster0.wtvzybp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client['travel_booking_db']

# Collections
users_collection = db['users']
trains_collection = db['trains']
bookings_collection = db['bookings']

# -------------------- Routes --------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if users_collection.find_one({'email': email}):
            flash('Email already exists!', 'error')
            return render_template('register.html')
        hashed_password = generate_password_hash(password)
        users_collection.insert_one({'email': email, 'password': hashed_password})
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'email' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users_collection.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['email'] = email
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('email', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))
    user_email = session['email']
    bookings = list(bookings_collection.find({'user_email': user_email}).sort('booking_date', -1))
    for b in bookings:
        b['_id'] = str(b['_id'])
    return render_template('dashboard.html', username=user_email, bookings=bookings)

# -------------------- Bus Booking --------------------

@app.route('/bus')
def bus():
    return render_template('bus.html')

@app.route('/confirm_bus_details')
def confirm_bus_details():
    seats_param = request.args.get('seats', '')
    selected_seats = seats_param.split(',') if seats_param else []
    booking = {
        "name": request.args.get("name"),
        "source": request.args.get("source"),
        "destination": request.args.get("destination"),
        "travel_date": request.args.get("date"),
        "time": request.args.get("time"),
        "type": request.args.get("type"),
        "num_persons": int(request.args.get("persons", 1)),
        "price_per_person": int(request.args.get("price", 0)),
        "selected_seats": selected_seats,
        "total_price": int(request.args.get("price", 0)) * len(selected_seats)
    }
    return render_template("confirm_bus_details.html", booking=booking)

@app.route('/final_confirm_booking', methods=['POST'])
def final_confirm_booking():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'User not logged in'}), 401
    data = request.get_json()
    try:
        booking_data = {
            'name': data['name'],
            'source': data['source'],
            'destination': data['destination'],
            'time': data['time'],
            'type': data['type'],
            'travel_date': data['date'],
            'num_persons': int(data['persons']),
            'price_per_person': float(data['price']),
            'total_price': float(data['total']),
            'selected_seats': data['seats'],
            'booking_type': 'bus',
            'booking_date': datetime.now().isoformat(),
            'user_email': session['email']
        }
        bookings_collection.insert_one(booking_data)
        return jsonify({'success': True, 'redirect': url_for('dashboard')})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# -------------------- Train Booking --------------------

@app.route('/train')
def train():
    return render_template('train.html')

@app.route('/api/trains_search')
def api_trains_search():
    source = request.args.get('source')
    destination = request.args.get('destination')
    date = request.args.get('date')
    coach_type = request.args.get('coach')

    query = {'source': source, 'destination': destination}
    matching_trains = list(trains_collection.find(query))

    filtered_trains = []
    for train in matching_trains:
        if train.get('date') == date and coach_type in train.get('coaches', {}):
            train['_id'] = str(train['_id'])
            train['price'] = train['coaches'][coach_type]
            train['selected_coach'] = coach_type
            filtered_trains.append(train)

    return jsonify(filtered_trains)

@app.route('/select_train_seats')
def select_train_seats():
    if 'email' not in session:
        return redirect(url_for('login'))

    booking_data = {
        'name': request.args.get('name'),
        'train_number': request.args.get('number'),
        'source': request.args.get('source'),
        'destination': request.args.get('destination'),
        'travel_date': request.args.get('date'),
        'coach': request.args.get('coach'),
        'price': float(request.args.get('price')),
        'persons': int(request.args.get('persons')),
        'departure': request.args.get('departure'),
        'arrival': request.args.get('arrival')
    }

    existing_bookings = bookings_collection.find({
        'train_number': booking_data['train_number'],
        'travel_date': booking_data['travel_date'],
        'selected_coach': booking_data['coach'],
        'booking_type': 'train'
    })

    booked_seats = []
    for b in existing_bookings:
        booked_seats.extend(b.get('selected_seats', []))
    booked_seats = [str(seat) for seat in booked_seats]

    return render_template('select_train_seats.html', booking=booking_data, booked_seats=booked_seats)

@app.route('/confirm_train_details')
def confirm_train_details():
    if 'email' not in session:
        return redirect(url_for('login'))
    seats = request.args.get('seats', '').split(',')
    booking = {
        'name': request.args.get('name'),
        'train_number': request.args.get('trainNumber'),
        'source': request.args.get('source'),
        'destination': request.args.get('destination'),
        'departure_time': request.args.get('departureTime'),
        'arrival_time': request.args.get('arrivalTime'),
        'price_per_person': float(request.args.get('price')),
        'travel_date': request.args.get('date'),
        'num_persons': int(request.args.get('persons')),
        'selected_coach': request.args.get('coach'),
        'selected_seats': seats,
        'total_price': float(request.args.get('price')) * len(seats),
        'booking_type': 'train',
        'user_email': session['email']
    }
    session['pending_booking'] = booking
    return render_template('confirm_train_details.html', booking=booking)

@app.route('/final_confirm_train_booking', methods=['POST'])
def final_confirm_train_booking():
    if 'email' not in session:
        return jsonify({'success': False}), 401
    booking = session.pop('pending_booking', None)
    if not booking:
        return jsonify({'success': False, 'message': 'No pending booking'}), 400
    booking['booking_date'] = datetime.now().isoformat()
    bookings_collection.insert_one(booking)
    return jsonify({'success': True, 'redirect': url_for('dashboard')})

# -------------------- Flight Booking --------------------

@app.route('/flight')
def flight():
    return render_template('flight.html')

@app.route('/select_flight_seats')
def select_flight_seats():
    if 'email' not in session:
        return redirect(url_for('login'))
    flight = {
        'flight_id': request.args.get('flight_id'),
        'airline': request.args.get('airline'),
        'flight_number': request.args.get('flight_number'),
        'source': request.args.get('source'),
        'destination': request.args.get('destination'),
        'departure_time': request.args.get('departure'),
        'arrival_time': request.args.get('arrival'),
        'travel_date': request.args.get('date'),
        'num_persons': int(request.args.get('passengers')),
        'price_per_person': float(request.args.get('price'))
    }
    existing = bookings_collection.find({
        'flight_id': flight['flight_id'],
        'travel_date': flight['travel_date'],
        'booking_type': 'flight'
    })
    booked = []
    for b in existing:
        booked += b.get('selected_seats', [])
    return render_template('select_flight_seats.html', flight=flight, booked_seats=booked)

@app.route('/confirm_flight_details')
def confirm_flight_details():
    if 'email' not in session:
        return redirect(url_for('login'))
    selected_seats = request.args.get('seats', '').split(',')
    booking = {
        'flight_id': request.args['flight_id'],
        'airline': request.args['airline'],
        'flight_number': request.args['flight_number'],
        'source': request.args['source'],
        'destination': request.args['destination'],
        'departure_time': request.args['departure'],
        'arrival_time': request.args['arrival'],
        'travel_date': request.args['date'],
        'num_persons': int(request.args['passengers']),
        'price_per_person': float(request.args['price']),
        'selected_seats': selected_seats,
        'total_price': float(request.args['price']) * len(selected_seats),
        'booking_type': 'flight',
        'user_email': session['email']
    }
    session['pending_booking'] = booking
    return render_template('confirm_flight_details.html', booking=booking)

@app.route('/confirm_flight_booking', methods=['POST'])
def confirm_flight_booking():
    if 'email' not in session:
        return redirect(url_for('login'))
    booking = session.pop('pending_booking', None)
    if booking:
        booking['booking_date'] = datetime.now().isoformat()
        bookings_collection.insert_one(booking)
        flash('Flight booking confirmed!', 'success')
    return redirect(url_for('dashboard'))

# -------------------- Hotel Booking --------------------

@app.route('/hotel')
def hotel():
    return render_template('hotel.html')

@app.route('/confirm_hotel_details')
def confirm_hotel_details():
    checkin = datetime.fromisoformat(request.args['checkin'])
    checkout = datetime.fromisoformat(request.args['checkout'])
    nights = (checkout - checkin).days
    booking = {
        'name': request.args['name'],
        'location': request.args['location'],
        'checkin_date': request.args['checkin'],
        'checkout_date': request.args['checkout'],
        'num_rooms': int(request.args['rooms']),
        'num_guests': int(request.args['guests']),
        'price_per_night': float(request.args['price']),
        'rating': int(request.args['rating']),
        'total_price': float(request.args['price']) * int(request.args['rooms']) * nights,
        'nights': nights,
        'booking_type': 'hotel',
        'user_email': session['email']
    }
    session['pending_booking'] = booking
    return render_template('confirm_hotel_details.html', booking=booking)

@app.route('/confirm_hotel_booking', methods=['POST'])
def confirm_hotel_booking():
    if 'email' not in session:
        return redirect(url_for('login'))
    booking = session.pop('pending_booking', None)
    if booking:
        booking['booking_date'] = datetime.now().isoformat()
        bookings_collection.insert_one(booking)
        flash('Hotel booking confirmed!', 'success')
    return redirect(url_for('dashboard'))

# -------------------- Cancel Booking --------------------

@app.route('/cancel_booking', methods=['POST'])
def cancel_booking():
    if 'email' not in session:
        return redirect(url_for('login'))
    booking_id = request.form['booking_id']
    bookings_collection.delete_one({'_id': ObjectId(booking_id), 'user_email': session['email']})
    flash('Booking cancelled successfully.', 'info')
    return redirect(url_for('dashboard'))

# -------------------- Sample Train Data --------------------

def insert_sample_train_data():
    if trains_collection.count_documents({}) == 0:
        today = datetime.today()
        sample_dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(5)]
        base_trains = [
            {
                "name": "Duronto Express",
                "train_number": "12285",
                "source": "Hyderabad",
                "destination": "Delhi",
                "departure_time": "07:00 AM",
                "arrival_time": "05:00 AM (next day)",
                "coaches": {
                    "Sleeper": 800,
                    "AC 3-Tier": 1500,
                    "AC 2-Tier": 2200,
                    "AC First Class": 3200
                }
            },
            {
                "name": "AP Express",
                "train_number": "12723",
                "source": "Hyderabad",
                "destination": "Vijayawada",
                "departure_time": "09:00 AM",
                "arrival_time": "03:00 PM",
                "coaches": {
                    "Sleeper": 300,
                    "AC 3-Tier": 550,
                    "AC 2-Tier": 800,
                    "AC First Class": 1500
                }
            },
            {
                "name": "Chennai Express",
                "train_number": "12728",
                "source": "Hyderabad",
                "destination": "Chennai",
                "departure_time": "20:00",
                "arrival_time": "08:00",
                "coaches": {
                    "Sleeper": 550,
                    "AC 3-Tier": 1000,
                    "AC 2-Tier": 1500,
                    "AC First Class": 2000
                }
            }
        ]
        docs = []
        for date in sample_dates:
            for train in base_trains:
                t = train.copy()
                t['date'] = date
                docs.append(t)
        trains_collection.insert_many(docs)

# -------------------- Main --------------------

if __name__ == '__main__':
    insert_sample_train_data()
    app.run(debug=True)