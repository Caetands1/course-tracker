CREATE TABLE users (
    userID INTEGER PRIMARY KEY,
    authcookies TEXT
);

CREATE TABLE courses (
    courseID TEXT PRIMARY KEY,
    title TEXT
);

CREATE TABLE user_course (
    userID INTEGER,
    courseID TEXT,
    PRIMARY KEY (userID, courseID),
    FOREIGN KEY (userID) REFERENCES users(userID),
    FOREIGN KEY (courseID) REFERENCES courses(courseID)
)