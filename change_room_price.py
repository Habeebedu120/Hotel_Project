# update_price.py (run with flask shell or include at top of file temporarily)
from app import db, RoomType, app

with app.app_context():
    r = RoomType.query.filter_by(name='Horizon Family Suite').first()
    if r:
        r.base_price =  4700000   # new price in Naira
        db.session.commit()
        print('Updated', r.name, r.base_price)
    else:
        print('RoomType not found')
