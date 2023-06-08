import bcrypt

def hash_password(password):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return salt, hashed_password

def verify_password(password,salt, hashed_password):
    hashed_attempt = bcrypt.hashpw(password.encode('utf-8'), salt)

    return hashed_password == hashed_attempt
