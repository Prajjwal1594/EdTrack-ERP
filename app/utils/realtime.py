from app import socketio
from datetime import datetime

def broadcast_student_update(student):
    """
    Broadcasts a holistic score and activity update to rooms 
    subscribed to this student (e.g. parents, faculty).
    """
    room = f"student_{student.id}"
    socketio.emit(
        "activity_update",
        {
            "student_id": student.id,
            "student_name": student.user.name,
            "holistic_score": student.holistic_growth_score(),
            "holistic_rating": student.holistic_rating,
            "timestamp": datetime.utcnow().isoformat(),
        },
        room=room
    )

def broadcast_notification(user_id, notification_data):
    """
    Sends a real-time notification to a specific user.
    """
    room = f"user_{user_id}"
    socketio.emit("new_notification", notification_data, room=room)
