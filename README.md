# FT_TRANSCENDENCE
A single-page application website for real-time multiplayer arcade games.
Written in JavaScript and Python, using the Django framework with a microservices architecture.
Using PostgreSQL to store user data and game history.
Using Docker to build the server.

## Games
Games can be played locally on one computer and remotely between users.
There is a choice between a quick match or a tournament.
Both games run server-side.

#### Pong:
Choice between a classic 2D scheme or advanced 3D visuals.

#### Snake:

## User Management
- Users can subscribe and log in to the website in a secure way.
- Users can update their information.
- Users can upload an avatar, with a default option if none is provided.
- Users can add others as friends and view their online status.
- User profiles display stats, such as wins and losses.
- Each user has a Match History including 1v1 games, dates, and relevant details, accessible to logged-in users.
- remote authentication is integrated with OAuth and available to 42 members.
