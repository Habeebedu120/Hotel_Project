import os
from datetime import datetime
from functools import wraps
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from sqlalchemy import event


from flask import (
    Flask, render_template, request, redirect, url_for, flash, abort, Response
)
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from dotenv import load_dotenv

# auth/password helpers
from werkzeug.security import generate_password_hash, check_password_hash

# flask-login
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required



app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret')

load_dotenv()  # load .env file if present

# DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 'sqlite:///dev.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Mail
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = ('Habeeb Empyrean Hotel & Resort', os.getenv('MAIL_USERNAME'))
mail = Mail(app)


# ----------------- Updated Models -----------------
class RoomType(db.Model):
    __tablename__ = 'room_types'  # double underscores
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    description = db.Column(db.Text)
    base_price = db.Column(db.Integer, nullable=False)
    total_rooms = db.Column(db.Integer, nullable=False)
    available_rooms = db.Column(db.Integer, nullable=False)
    max_guests = db.Column(db.Integer, nullable=False)
    features = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'base_price': self.base_price,
            'total_rooms': self.total_rooms,
            'available_rooms': self.available_rooms,
            'max_guests': self.max_guests,
            'features': self.features
        }
class Booking(db.Model):
    __tablename__ = 'bookings'  # double underscores
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    phone = db.Column(db.String(50))
    checkin = db.Column(db.Date, nullable=False)
    checkout = db.Column(db.Date, nullable=False)
    room_type_id = db.Column(db.Integer, db.ForeignKey('room_types.id'), nullable=False)
    room_type = db.relationship('RoomType', backref='bookings')
    guests = db.Column(db.Integer, default=1)
    total_price = db.Column(db.Integer)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cancellation_reason = db.Column(db.Text)
    cancelled_at = db.Column(db.DateTime)

    def is_pending(self):
        return self.status == 'pending'

    def calculate_price(self):
        # Calculate price based on number of nights
        nights = (self.checkout - self.checkin).days
        return nights * self.room_type.base_price


class AdminUser(db.Model, UserMixin):
    _tablename_ = 'admin_users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    # Add role flags if you want more than one type of admin later
    is_superadmin = db.Column(db.Boolean, default=True)

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    @property
    def is_admin(self):
        # simple convenience property for route guards
        return True  # all AdminUser entries are admins; refine as needed


# create tables (dev only; use migrations in prod)
with app.app_context():
    db.create_all()

# ----------------- Flask-Login setup -----------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = "Please log in to access the admin area."

@login_manager.user_loader
def load_user(user_id):
    try:
        return AdminUser.query.get(int(user_id))
    except Exception:
        return None

# Seed an admin from environment variables (DEV convenience)
def ensure_admin_from_env():
    env_user = os.getenv('ADMIN_USER')
    env_pass = os.getenv('ADMIN_PASSWORD')
    if not env_user or not env_pass:
        app.logger.info("No ADMIN_USER/ADMIN_PASSWORD in env; skipping admin seed.")
        return

    existing = AdminUser.query.filter_by(username=env_user).first()
    if existing:
        app.logger.info("Admin user already exists; skipping seed.")
        return

    app.logger.info("Creating admin user from env variables.")
    admin = AdminUser(username=env_user)
    admin.set_password(env_pass)
    db.session.add(admin)
    db.session.commit()

def initialize_room_types():
    """Initialize room types with availability counts"""
    room_types = [
        {
            'name': 'Luxury Suite',
            'description': 'Private terrace • Panoramic ocean views • Butler service • One Bedroom',
            'base_price': 1500000,
            'total_rooms': 10,
            'available_rooms': 10,
            'max_guests': 2,
            'features': 'Private terrace, Ocean views, Butler service, King bed'
        },
        {
            'name': 'Imperial Sky Suite', 
            'description': 'Two-level suite with private plunge pool and observatory lounge.',
            'base_price': 2400000,
            'total_rooms': 5,
            'available_rooms': 5,
            'max_guests': 4,
            'features': 'Two-level, Plunge pool, Observatory lounge, 2 bedrooms'
        },
        {
            'name': 'Ocean Paragon Suite',
            'description': 'Floor-to-ceiling windows, private butler, complimentary yacht transfer.',
            'base_price': 3700000,
            'total_rooms': 3,
            'available_rooms': 3,
            'max_guests': 4,
            'features': 'Floor-to-ceiling windows, Private butler, Yacht transfer, 2 bedrooms'
        },
        {
            'name': 'Celestial Presidential',
            'description': 'Private chef, panoramic terrace, cool in-room spa pavilion.',
            'base_price': 4100000,
            'total_rooms': 2,
            'available_rooms': 2,
            'max_guests': 4,
            'features': 'Private chef, Spa pavilion, Panoramic terrace, 2 bedrooms'
        },
        {
            'name': 'Garden View Suite',
            'description': 'Tranquil garden-facing suite with balcony and complimentary breakfast.',
            'base_price': 2000000,
            'total_rooms': 8,
            'available_rooms': 8,
            'max_guests': 3,
            'features': 'Garden view, Balcony, Breakfast included, Queen bed'
        },
        {
            'name': 'Horizon Family Suite',
            'description': 'Spacious family suite with two bedrooms, kitchenette and kids play area.',
            'base_price': 4700000,
            'total_rooms': 6,
            'available_rooms': 6,
            'max_guests': 5,
            'features': '2 bedrooms, Kitchenette, Family-friendly, Extra bed available'
        }

    ]
    
    for room_data in room_types:
        existing = RoomType.query.filter_by(name=room_data['name']).first()
        if not existing:
            room = RoomType(**room_data)
            db.session.add(room)
    
    db.session.commit()    

with app.app_context():
    db.create_all()
    ensure_admin_from_env()
    initialize_room_types()

# ----------------- Email helper -----------------
def send_confirmation_email(booking: Booking) -> bool:
    """
    Send a confirmation email to the guest after a booking is confirmed.
    Returns True on success, False on failure. Logs detailed errors for debugging.
    """
    # Quick sanity checks
    recipient = getattr(booking, 'email', None)
    if not recipient:
        app.logger.warning("send_confirmation_email: booking has no email address (booking id: %s).", getattr(booking, 'id', 'N/A'))
        return False

    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
        app.logger.warning("send_confirmation_email: mail credentials not set; skipping email send.")
        return False

    # Safe room/suite retrieval
    suite_name = getattr(getattr(booking, 'room_type', None), 'name', 'N/A')

    try:
        subject = f'Habeeb Empyrean — Booking Confirmed (Ref #{booking.id})'

        plain_body = (
            f"Dear {booking.full_name},\n\n"
            "Thank you for booking at Habeeb Empyrean Hotel and Resort — your booking has been confirmed.\n\n"
            f"Booking reference: {booking.id}\n"
            f"Suite: {suite_name}\n"
            f"Check-in: {booking.checkin}\n"
            f"Check-out: {booking.checkout}\n\n"
            "We look forward to hosting you. If you need anything before arrival, reply to this email or call our concierge.\n\n"
            "Warm regards,\n"
            "Habeeb Empyrean Hotel & Resort Concierge\n"
        )

        # Optional HTML body (email clients prefer HTML)
        html_body = f"""
        <p>Dear {booking.full_name},</p>
        <p>Thank you for booking at <strong>Habeeb Empyrean Hotel and Resort</strong> — your booking has been <strong>confirmed</strong>.</p>
        <ul>
          <li><strong>Booking reference:</strong> {booking.id}</li>
          <li><strong>Suite:</strong> {suite_name}</li>
          <li><strong>Check-in:</strong> {booking.checkin}</li>
          <li><strong>Check-out:</strong> {booking.checkout}</li>
        </ul>
        <p>We look forward to hosting you. If you need anything before arrival, reply to this email or call our concierge.</p>
        <p>Warm regards,<br>Habeeb Empyrean Hotel &amp; Resort Concierge</p>
        """

        msg = Message(subject=subject, recipients=[recipient])
        msg.body = plain_body
        msg.html = html_body

        mail.send(msg)
        app.logger.info("send_confirmation_email: confirmation email sent to %s for booking #%s", recipient, booking.id)
        return True

    except Exception as exc:
        # Log detailed exception info to help debugging
        app.logger.exception("send_confirmation_email: failed to send confirmation email for booking #%s. Exception: %s", getattr(booking, 'id', 'N/A'), exc)
        return False

    

# Cancellation email helper + hotel notification

def send_cancellation_email(booking: Booking) -> bool:
    """
    Send an email to the booker notifying them their booking was cancelled.
    Uses booking.cancellation_reason / cancelled_at if available.
    """
    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
        app.logger.warning("Mail credentials not set; skipping cancellation email.")
        return False

    # safe suite name (fallback to 'N/A' if relationship missing)
    suite_name = getattr(getattr(booking, 'room_type', None), 'name', 'N/A')

    try:
        subject = f'Habeeb Empyrean — Booking Cancelled (Ref #{booking.id})'
        msg = Message(subject=subject, recipients=[booking.email])

        body_lines = [
            f"Dear {booking.full_name},",
            "",
            "We regret to inform you that your booking at Habeeb Empyrean Hotel and Resort has been cancelled",
            "",
            f"Booking reference: {booking.id}",
            f"Suite: {suite_name}",
            f"Check-in: {booking.checkin}",
            f"Check-out: {booking.checkout}",
        ]
        if booking.cancelled_at:
            body_lines.append(f"Cancelled at: {booking.cancelled_at}")
        if booking.cancellation_reason:
            body_lines.extend(["", "Reason for cancellation:", booking.cancellation_reason])

        body_lines.extend([
            "",
            "If you believe this is an error or would like help rebooking, please reply to this email or call our concierge.",
            "",
            "Warm regards,",
            "Habeeb Empyrean Hotel & Resort Concierge"
        ])

        msg.body = "\n".join(body_lines)
        mail.send(msg)
        app.logger.info("Cancellation email sent to %s for booking #%s", booking.email, booking.id)
        return True
    except Exception as exc:
        app.logger.exception("Failed to send cancellation email for booking #%s. Exception: %s", booking.id, exc)
        return False



def notify_hotel_of_cancellation(booking: Booking) -> bool:
    """
    Send a notification to the hotel/staff that a booking was cancelled.
    Uses HOTEL_NOTIFICATION_EMAIL env var or MAIL_USERNAME fallback.
    """
    hotel_email = os.getenv('HOTEL_NOTIFICATION_EMAIL') or app.config.get('MAIL_USERNAME')
    if not hotel_email:
        app.logger.warning("No HOTEL_NOTIFICATION_EMAIL or MAIL_USERNAME configured; skipping hotel cancellation notification.")
        return False

    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
        app.logger.warning("Mail credentials not set; skipping hotel cancellation notification.")
        return False

    try:
        try:
            admin_link = url_for('admin_booking_detail', booking_id=booking.id, _external=True)
        except Exception:
            admin_link = f"Booking admin URL: /admin/booking/{booking.id}"

        # safe suite name
        suite_name = getattr(getattr(booking, 'room_type', None), 'name', 'N/A')

        msg = Message(
            subject=f'Booking Cancelled — Ref #{booking.id}',
            recipients=[hotel_email]
        )

        body_lines = [
            "A booking has been cancelled at Habeeb Empyrean Hotel & Resort.",
            "",
            f"Reference: {booking.id}",
            f"Name: {booking.full_name}",
            f"Email: {booking.email}",
            f"Phone: {booking.phone or 'N/A'}",
            f"Suite: {suite_name}",
            f"Check-in: {booking.checkin}",
            f"Check-out: {booking.checkout}",
            f"Status: {booking.status}",
            f"Created at: {booking.created_at}",
        ]
        if booking.cancelled_at:
            body_lines.append(f"Cancelled at: {booking.cancelled_at}")
        if booking.cancellation_reason:
            body_lines.extend(["", "Cancellation reason:", booking.cancellation_reason])

        body_lines.extend(["", f"Admin details: {admin_link}"])
        msg.body = "\n".join(body_lines)

        mail.send(msg)
        app.logger.info("Hotel cancellation notification sent for booking #%s", booking.id)
        return True
    except Exception as exc:
        app.logger.exception("Failed to send hotel cancellation notification for booking #%s. Exception: %s", booking.id, exc)
        return False


# ----------------- Public routes -----------------
@app.route('/')
def index():
    room_types = RoomType.query.all()
    return render_template('index.html', 
                         year=datetime.now().year,
                         room_types=room_types,
                         today=datetime.now().date())

@app.route('/book', methods=['POST'])
def book():
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    checkin_str = request.form.get('checkin', '').strip()
    checkout_str = request.form.get('checkout', '').strip()
    room_type_id = request.form.get('room_type_id', type=int)
    guests = request.form.get('guests', 1, type=int)

    errors = []
    
    # Validation
    if not full_name: errors.append('Full name required.')
    if not email: errors.append('Email required.')
    if not checkin_str or not checkout_str:
        errors.append('Check-in and Check-out required.')
    if not room_type_id:
        errors.append('Room type is required.')

    # Get room type and check availability
    room_type = RoomType.query.get(room_type_id)
    if not room_type:
        errors.append('Invalid room type selected.')
    elif room_type.available_rooms < 1:
        errors.append(f'Sorry, no {room_type.name} rooms available.')

    checkin = checkout = None
    try:
        if checkin_str: checkin = datetime.strptime(checkin_str, '%Y-%m-%d').date()
        if checkout_str: checkout = datetime.strptime(checkout_str, '%Y-%m-%d').date()
        if checkin and checkout:
            if checkin >= checkout:
                errors.append('Check-in must be before check-out.')
            if checkin < datetime.now().date():
                errors.append('Check-in date cannot be in the past.')
    except ValueError:
        errors.append('Invalid date format.')

    if guests > room_type.max_guests:
        errors.append(f'Maximum guests for this room is {room_type.max_guests}.')

    if errors:
        for e in errors:
            flash(e, 'danger')
        return redirect(url_for('index'))

    # Create booking
    booking = Booking(
        full_name=full_name,
        email=email,
        phone=phone,
        checkin=checkin,
        checkout=checkout,
        room_type=room_type,
        guests=guests,
        status='pending'
    )
    booking.total_price = booking.calculate_price()

    try:
        # Deduct available room
        room_type.available_rooms -= 1
        
        db.session.add(booking)
        db.session.commit()

        # 1️⃣ Send immediate email to customer
        try:
            send_booking_received_email(booking)
        except Exception:
            app.logger.exception("Failed to send immediate customer booking email")

        # 2️⃣ Notify hotel staff immediately
        try:
            notify_hotel_of_new_booking(booking)
        except Exception:
            app.logger.exception("Failed to notify hotel staff")

        flash(f'Thanks {full_name}! Your booking is received and awaiting confirmation. {room_type.name} availability updated.', 'success')
        
    except Exception as e:
        db.session.rollback()
        app.logger.exception("DB save error")
        flash('Could not save booking. Try again later.', 'danger')
    
    return redirect(url_for('index'))

def send_booking_received_email(booking: Booking):
    """
    Send an immediate email to the customer acknowledging receipt of their booking request.
    Status is still pending; final confirmation will come after hotel approval.
    """
    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
        app.logger.warning("Mail credentials not set; skipping booking received email.")
        return False

    try:
        msg = Message(
            subject=f'Habeeb Empyrean — Booking Received (Ref #{booking.id})',
            recipients=[booking.email]
        )
        msg.body = f"""Dear {booking.full_name},

Thank you for booking at Habeeb Empyrean Hotel & Resort. Your booking request has been received and is awaiting hotel confirmation.

Booking reference: {booking.id}
Suite: {booking.room_type.name}
Check-in: {booking.checkin}
Check-out: {booking.checkout}
Guests: {booking.guests}

We will notify you once the hotel confirms your booking.

Warm regards,
Habeeb Empyrean Hotel & Resort Concierge
"""
        mail.send(msg)
        app.logger.info("Booking received email sent to %s for booking #%s", booking.email, booking.id)
        return True
    except Exception:
        app.logger.exception("Failed to send booking received email for booking #%s", booking.id)
        return False



# Hotel_email_notification helper
def notify_hotel_of_new_booking(booking: Booking):
    """
    Send an email to the hotel/admin address notifying them a new booking was received.
    Uses HOTEL_NOTIFICATION_EMAIL env var; falls back to MAIL_USERNAME.
    Returns True if sent, False otherwise.
    """
    hotel_email = os.getenv('HOTEL_NOTIFICATION_EMAIL') or app.config.get('MAIL_USERNAME')
    if not hotel_email:
        app.logger.warning("No HOTEL_NOTIFICATION_EMAIL or MAIL_USERNAME configured; skipping hotel notification.")
        return False

    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
        app.logger.warning("Mail credentials not set; skipping hotel notification.")
        return False

    try:
        admin_link = None
        try:
            # if your app is running with proper SERVER_NAME this will generate an absolute URL
            admin_link = url_for('admin_booking_detail', booking_id=booking.id, _external=True)
        except Exception:
            # ignore — url_for may fail outside request context or without SERVER_NAME
            admin_link = f"Booking admin URL: /admin/booking/{booking.id}"

        msg = Message(
            subject=f'New Booking Request — Ref #{booking.id}',
            recipients=[hotel_email]
        )
        msg.body = f"""New booking received at Habeeb Empyrean Hotel & Resort.

Reference: {booking.id}
Name: {booking.full_name}
Email: {booking.email}
Phone: {booking.phone or 'N/A'}
Suite: {booking.suite}
Check-in: {booking.checkin}
Check-out: {booking.checkout}
Status: {booking.status}
Created at: {booking.created_at}

"""
        mail.send(msg)
        app.logger.info("Hotel notification email sent for booking #%s", booking.id)
        return True
    except Exception:
        app.logger.exception("Failed to send hotel notification email for booking #%s", booking.id)
        return False

def notify_hotel_of_new_booking(booking: Booking) -> bool:
    """
    Send an email to the hotel/admin address notifying them a new booking was received.
    Uses HOTEL_NOTIFICATION_EMAIL env var; falls back to MAIL_USERNAME.
    Supports comma-separated HOTEL_NOTIFICATION_EMAIL for multiple recipients.
    Returns True if sent, False otherwise.
    """
    # Resolve recipients: allow comma-separated list in env
    raw = os.getenv('HOTEL_NOTIFICATION_EMAIL') or app.config.get('MAIL_USERNAME')
    if not raw:
        app.logger.warning("notify_hotel_of_new_booking: No HOTEL_NOTIFICATION_EMAIL or MAIL_USERNAME configured; skipping hotel notification.")
        return False

    recipients = [r.strip() for r in raw.split(',') if r.strip()]
    if not recipients:
        app.logger.warning("notify_hotel_of_new_booking: HOTEL_NOTIFICATION_EMAIL is present but empty after parsing.")
        return False

    # Ensure mail credentials present
    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
        app.logger.warning("notify_hotel_of_new_booking: Mail credentials not set; skipping hotel notification.")
        return False

    # Safe admin link (try external URL, else fallback relative)
    try:
        admin_link = url_for('admin_booking_detail', booking_id=booking.id, _external=True)
    except Exception:
        admin_link = f"/admin/booking/{booking.id}"

    # Use room_type name safely (some older bookings might not have relationship loaded)
    suite_name = getattr(getattr(booking, 'room_type', None), 'name', 'N/A')

    subject = f'New Booking Request — Ref #{booking.id}'
    body_lines = [
        "New booking received at Habeeb Empyrean Hotel & Resort.",
        "",
        f"Reference: {booking.id}",
        f"Name: {booking.full_name}",
        f"Email: {booking.email}",
        f"Phone: {booking.phone or 'N/A'}",
        f"Suite: {suite_name}",
        f"Check-in: {booking.checkin}",
        f"Check-out: {booking.checkout}",
        f"Status: {booking.status}",
        f"Created at: {booking.created_at}",
        "",
        f"Admin page: {admin_link}"
    ]
    try:
        msg = Message(subject=subject, recipients=recipients)
        msg.body = "\n".join(body_lines)

        mail.send(msg)
        app.logger.info("notify_hotel_of_new_booking: email sent to %s for booking #%s", ", ".join(recipients), booking.id)
        return True
    except Exception as exc:
        # Log exception and context for debugging
        app.logger.exception("notify_hotel_of_new_booking: failed to send email for booking #%s. Exception: %s", booking.id, exc)
        return False


# ----------------- Admin auth routes (flask-login) -----------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            flash('Username and password required.', 'danger')
            return redirect(url_for('admin_login'))

        user = AdminUser.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful.', 'success')
            next_page = request.args.get('next')
            # basic safety: don't redirect to external URL
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
            return redirect(url_for('admin_login'))

    return render_template('admin_login.html')


@app.route('/admin/logout', methods=['POST'])
@login_required
def admin_logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


# ----------------- Admin panel (protected) -----------------
def admin_only(f):
    """Decorator to enforce admin role beyond login_required if needed."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        # In this simple app, any logged-in AdminUser is an admin.
        # If you add roles later, check them here.
        return f(*args, **kwargs)
    return decorated


@app.route('/admin')
@admin_only
def admin_dashboard():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    q = Booking.query.order_by(Booking.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('admin_list.html', page_obj=q)


@app.route('/admin/booking/<int:booking_id>')
@admin_only
def admin_booking_detail(booking_id):
    b = Booking.query.get_or_404(booking_id)
    return render_template('admin_detail.html', booking=b)

def notify_staff_of_confirmation(booking: Booking) -> bool:
    """
    Notify hotel staff/admin that a booking was CONFIRMED.
    Uses HOTEL_NOTIFICATION_EMAIL or MAIL_USERNAME (supports comma-separated recipients).
    Ensures fallback to MAIL_USERNAME if recipients list is empty.
    Returns True on success, False on failure.
    """
    # Get recipients from env or MAIL_USERNAME
    raw = os.getenv('HOTEL_NOTIFICATION_EMAIL') or app.config.get('MAIL_USERNAME')
    
    if not raw:
        app.logger.warning(
            "notify_staff_of_confirmation: No HOTEL_NOTIFICATION_EMAIL or MAIL_USERNAME set; cannot notify staff."
        )
        return False

    # Split comma-separated emails and clean up whitespace
    recipients = [r.strip() for r in raw.split(',') if r.strip()]

    # Fallback: ensure at least MAIL_USERNAME is included
    if not recipients:
        fallback = app.config.get('MAIL_USERNAME')
        if fallback:
            recipients = [fallback]
            app.logger.info("notify_staff_of_confirmation: recipients empty, using fallback MAIL_USERNAME")
        else:
            app.logger.warning("notify_staff_of_confirmation: no valid recipients; aborting.")
            return False

    # Check mail credentials
    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
        app.logger.warning("notify_staff_of_confirmation: mail credentials not set; cannot send email.")
        return False

    # Safe room/suite name
    suite_name = getattr(getattr(booking, 'room_type', None), 'name', 'N/A')

    # Try generating absolute admin URL
    try:
        admin_link = url_for('admin_booking_detail', booking_id=booking.id, _external=True)
    except Exception:
        admin_link = f"/admin/booking/{booking.id}"

    subject = f'Booking Confirmed — Ref #{booking.id}'
    body_lines = [
        "A booking has been confirmed at Habeeb Empyrean Hotel & Resort.",
        "",
        f"Reference: {booking.id}",
        f"Name: {booking.full_name}",
        f"Email: {booking.email}",
        f"Phone: {booking.phone or 'N/A'}",
        f"Suite: {suite_name}",
        f"Check-in: {booking.checkin}",
        f"Check-out: {booking.checkout}",
        f"Guests: {booking.guests}",
        f"Status: {booking.status}",
        f"Created at: {booking.created_at}",
        "",
        f"Admin page: {admin_link}"
    ]

    try:
        app.logger.info(
            "notify_staff_of_confirmation: sending email to %s for booking #%s",
            ", ".join(recipients),
            booking.id
        )
        msg = Message(subject=subject, recipients=recipients)
        msg.body = "\n".join(body_lines)
        mail.send(msg)
        app.logger.info(
            "notify_staff_of_confirmation: email successfully sent to %s for booking #%s",
            ", ".join(recipients),
            booking.id
        )
        return True
    except Exception as exc:
        app.logger.exception(
            "notify_staff_of_confirmation: failed to send email for booking #%s. Exception: %s",
            booking.id,
            exc
        )
        return False


@app.route('/admin/booking/<int:booking_id>/status', methods=['POST'])
@admin_only
def admin_change_status(booking_id):
    b = Booking.query.get_or_404(booking_id)
    new_status = request.form.get('status')
    old_status = b.status
    if new_status not in ('pending', 'confirmed', 'cancelled'):
        flash('Invalid status', 'danger')
        return redirect(url_for('admin_booking_detail', booking_id=booking_id))

    # capture optional cancellation reason from admin form
    reason = request.form.get('reason', '').strip()

    # Handle room availability
    if new_status == 'cancelled' and old_status in ['pending', 'confirmed']:
        # Return room to availability
        b.room_type.available_rooms += 1
        b.cancellation_reason = reason
        b.cancelled_at = datetime.utcnow()
    
    elif old_status == 'cancelled' and new_status in ['pending', 'confirmed']:
        # Take room from availability if re-activating a cancelled booking
        if b.room_type.available_rooms > 0:
            b.room_type.available_rooms -= 1
        else:
            flash('Cannot confirm booking: no rooms available.', 'danger')
            return redirect(url_for('admin_booking_detail', booking_id=booking_id))

    b.status = new_status

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash('Could not update status', 'danger')
        return redirect(url_for('admin_booking_detail', booking_id=booking_id))

    # if changed to confirmed, send confirmation email
    if new_status == 'confirmed':
        ok_customer = send_confirmation_email(b)
        ok_staff = notify_staff_of_confirmation(b)
        if ok_customer and ok_staff:
            flash('Booking confirmed, confirmation email sent to guest and staff notified.', 'success')
        elif ok_customer and not ok_staff:
            flash('Booking confirmed and guest email sent, but staff notification failed.', 'warning')
        elif not ok_customer and ok_staff:
            flash('Booking confirmed and staff notified, but guest email failed to send.', 'warning')
        else:
            flash('Booking confirmed but email notifications failed.', 'warning')




    # if changed to cancelled, send cancellation email to the booker and notify hotel staff
    elif new_status == 'cancelled':
        ok_booker = send_cancellation_email(b)
        ok_hotel = notify_hotel_of_cancellation(b)
        if ok_booker and ok_hotel:
            flash('Booking cancelled. Booker and hotel notified by email.', 'success')
        elif ok_booker and not ok_hotel:
            flash('Booking cancelled and booker notified, but hotel notification failed.', 'warning')
        elif not ok_booker and ok_hotel:
            flash('Booking cancelled and hotel notified, but booker email failed.', 'warning')
        else:
            flash('Booking cancelled but email notifications failed.', 'warning')
    else:
        flash('Booking status updated.', 'success')

    return redirect(url_for('admin_booking_detail', booking_id=booking_id))

    


@app.route('/admin/booking/<int:booking_id>/delete', methods=['POST'])
@admin_only
def admin_delete_booking(booking_id):
    b = Booking.query.get_or_404(booking_id)
    try:
        db.session.delete(b)
        db.session.commit()
        flash('Booking deleted.', 'success')
    except Exception:
        db.session.rollback()
        flash('Could not delete booking.', 'danger')
    return redirect(url_for('admin_dashboard'))


# optional: route to create additional admin via a protected endpoint (disabled by default)
# you can enable if you want an admin UI for creating admins later.
@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(debug=True)