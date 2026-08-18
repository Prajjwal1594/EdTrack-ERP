from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.messages import bp
from app.models import Message, User, Notification
from app import db
from datetime import datetime
from sqlalchemy import or_


@bp.route('/')
@login_required
def inbox():
    messages = (Message.query
                .filter_by(recipient_id=current_user.id, is_deleted_recipient=False)
                .filter(Message.parent_id == None)
                .order_by(Message.sent_at.desc()).all())
    return render_template('messages/inbox.html', messages=messages)


@bp.route('/sent')
@login_required
def sent():
    messages = (Message.query
                .filter_by(sender_id=current_user.id, is_deleted_sender=False)
                .filter(Message.parent_id == None)
                .order_by(Message.sent_at.desc()).all())
    return render_template('messages/sent.html', messages=messages)


@bp.route('/compose', methods=['GET', 'POST'])
@login_required
def compose():
    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id', type=int)
        recipient = User.query.get(recipient_id)
        if not recipient:
            flash('Recipient not found.', 'danger')
            return redirect(url_for('messages.compose'))

        msg = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            subject=request.form.get('subject', '').strip(),
            body=request.form.get('body', '').strip()
        )
        db.session.add(msg)

        notif = Notification(
            user_id=recipient_id,
            type='message',
            title=f'New message from {current_user.name}',
            message=msg.subject,
            link=url_for('messages.view_message', mid=0)  # will update after commit
        )
        db.session.add(notif)
        db.session.commit()
        notif.link = url_for('messages.view_message', mid=msg.id)
        db.session.commit()
        flash('Message sent.', 'success')
        return redirect(url_for('messages.sent'))

    # Get recipients: faculty can message students/parents and vice versa
    recipients = User.query.filter(
        User.id != current_user.id,
        User.college_id == current_user.college_id,
        User.is_active == True
    ).order_by(User.role, User.name).all()

    preselect = request.args.get('to', type=int)
    return render_template('messages/compose.html', recipients=recipients, preselect=preselect)


@bp.route('/<int:mid>')
@login_required
def view_message(mid):
    msg = Message.query.get_or_404(mid)
    if msg.recipient_id != current_user.id and msg.sender_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('messages.inbox'))

    if msg.recipient_id == current_user.id and not msg.read_at:
        msg.read_at = datetime.utcnow()
        db.session.commit()

    # Get thread
    thread_root = msg
    while thread_root.parent_id:
        thread_root = thread_root.parent
    thread = _get_thread(thread_root)

    return render_template('messages/view.html', msg=msg, thread=thread, thread_root=thread_root)


def _get_thread(msg):
    result = [msg]
    for reply in msg.replies:
        result.extend(_get_thread(reply))
    return result


@bp.route('/<int:mid>/reply', methods=['POST'])
@login_required
def reply(mid):
    parent = Message.query.get_or_404(mid)
    recipient_id = parent.sender_id if parent.recipient_id == current_user.id else parent.recipient_id

    reply_msg = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        subject=f"Re: {parent.subject}",
        body=request.form.get('body', '').strip(),
        parent_id=parent.id
    )
    db.session.add(reply_msg)
    db.session.commit()
    flash('Reply sent.', 'success')
    return redirect(url_for('messages.view_message', mid=parent.id))


@bp.route('/<int:mid>/delete', methods=['POST'])
@login_required
def delete_message(mid):
    msg = Message.query.get_or_404(mid)
    if msg.sender_id == current_user.id:
        msg.is_deleted_sender = True
    if msg.recipient_id == current_user.id:
        msg.is_deleted_recipient = True
    db.session.commit()
    flash('Message deleted.', 'info')
    return redirect(url_for('messages.inbox'))


@bp.route('/unread-count')
@login_required
def unread_count():
    count = Message.query.filter_by(recipient_id=current_user.id, read_at=None).count()
    return jsonify({'count': count})
