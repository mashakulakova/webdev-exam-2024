from flask_login import current_user

class CheckUser:
    def __init__(self, record):
        self.record = record
    def create(self):
        return current_user.is_admin()
    def show(self):
        return True
    def edit(self):
        return current_user.is_admin() or current_user.is_moderator()
    def delete(self):
        return current_user.is_admin()
