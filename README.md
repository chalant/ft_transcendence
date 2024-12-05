# FT_TRANSCENDENCE
A single-page application website for real-time multiplayer arcade games.
Written in JavaScript and Python, using the Django framework with a microservices architecture.
Using PostgreSQL to store user data and game history.
Using Docker to build the server.

## User Management
- Users can subscribe and log into the website in a secure way.
- Users can update their information, including an avatar.
- Users can add others as friends and view their online status.
- User profiles display stats, such as wins and losses.
- Each user has a Match History including 1v1 games, dates, and relevant details, accessible to logged-in users.
- remote authentication is integrated with OAuth and available to '42' members.
- 
![Screenshot (71)](https://github.com/user-attachments/assets/ce50d88a-9026-4449-8f26-a6fa38386b98)
![Screenshot (74)](https://github.com/user-attachments/assets/0c3aaef3-c392-4084-9be6-df59b370103e)

## Games
Games can be played locally on one computer or remotely between users.
You can play a quick match or join a tournament.
Both games run server-side.

#### Pong:
Choice between a classic 2D scheme or 3D visuals.
![Screenshot (72)](https://github.com/user-attachments/assets/cbf4b1e6-5a41-4877-ac2a-51a9a5a9e6a9)
![Screenshot (82)](https://github.com/user-attachments/assets/7f807ea9-b8c5-4cb1-b0f6-7314ba28860b)

#### Snake:
![Screenshot (79)](https://github.com/user-attachments/assets/995f4441-9490-44ad-ba67-9ff0ca331bdd)

##### Tournament setup:
![Screenshot (68)](https://github.com/user-attachments/assets/f4e5e081-8975-4d74-8563-b0bd4f2ef622)
