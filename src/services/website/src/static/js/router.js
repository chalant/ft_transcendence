// Navigate to a new URL and update content
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

export const navigateTo = async url => {
    history.pushState(null, null, url);
    await router();
    const matches = url.match('https://[^/]*/');
    if (matches && matches.length) {
        window.dispatchEvent(new Event(url.substr(matches[0].length)));
    }
};

// Router function to handle routes
const router = async () => {
    const routes = [
        { path: "/", view: Home },
        { path: "/pong", view: Pong },
        { path: "/other-game", view: Other_game },
        { path: "/settings", view: Settings },
        { path: "/friends", view: Friends },
        { path: "/stats", view: Stats },
        { path: "/user/:username", view: UserProfile }
    ];

    // Find a matching route or return 404
    const potentialMatches = routes.map(route => {
        const pathRegex = new RegExp("^" + route.path.replace(/:\w+/g, "(.+)") + "$");
        return {
            route: route,
            result: location.pathname.match(pathRegex)
        };
    });

    let match = potentialMatches.find(potentialMatch => potentialMatch.result);

    if (!match) {
        match = {
            route: { path: "/404", view: () => "<div class=\"text-center\"><h1>404 - Page Not Found</h1><p>Please go back to another page, using the buttons above.</p></div>" },
            result: [location.pathname]
        };
    }

    const params = match.result.slice(1);

    // Render the view
    document.getElementById('app').innerHTML = await match.route.view(...params);
};

// View functions
const Home = () => `
    <div class="text-center">
        <h1>Home Page</h1>
        <p>Welcome to ft_transcendence!</p>
    </div>
`;

const Pong = () => `
    <div class="row">
        <div class="col text-center">
            <div class="canvas-container">
                <canvas id="gameCanvas" class="w-100 border"></canvas>
            </div>
        </div>
        <div id="game-button-container">
            <button class="btn btn-succes me-2" id="game-button" type="button">find game</button>
        </div>
    </div>
`;

const Other_game = () => `
    <div class="row">
    <div class="col text-center">
        <div class="canvas-container">
            <canvas id="gameCanvas" class="w-100 border"></canvas>
        </div>
    </div>
    </div>
`;

const Settings = async () => {
    const token = localStorage.getItem('auth_token');
    const response = await fetch('/auth/is_authenticated/', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
            'Authorization': `Bearer ${token}`
        }
    });
    const data = await response.json();

    if (data.status === 0) {
        return `
            <div class="text-center">
                <h1>Access Denied</h1>
                <p>You need to be logged in to view this page.</p>
            </div>
        `;
    }

    const { username, profile_picture } = data.user;

    return`
    <div class="text-center">
        <h1>Settings Page</h1>
        <p>Manage your profile settings here.</p>

        <!-- Change Profile Picture -->
        <div id="profile-picture-change" class="mb-3">
            <h4>Change Profile Picture</h4>
            <form id="profile-picture-form" enctype="multipart/form-data">
                <img src="${profile_picture}" alt="Profile Picture" class="profile-picture-preview">
                <br>
                <input type="file" id="profile-picture-input" name="profile_picture" accept="image/*" required>
                <br>
                <button type="submit" class="btn btn-primary mt-2">Upload</button>
            </form>
        </div>

        <!-- Change Username -->
        <div id="username-change" class="mb-3">
            <h4>Change Username</h4>
            <form id="username-change-form">
                <input type="text" id="new-username" name="username" value="${username}" placeholder="New Username" required>
                <br>
                <button type="submit" class="btn btn-primary mt-2">Change Username</button>
            </form>
        </div>

        <!-- Change Password -->
        <div id="password-change" class="mb-3">
            <h4>Change Password</h4>
            <form id="password-change-form">
                <input type="password" id="current-password" name="current_password" placeholder="Current Password" required>
                <br>
                <input type="password" id="new-password" name="new_password" placeholder="New Password" required>
                <br>
                <input type="password" id="confirm-new-password" name="confirm_new_password" placeholder="Confirm New Password" required>
                <br>
                <button type="submit" class="btn btn-primary mt-2">Change Password</button>
            </form>
        </div>
    </div>
    `;
};

const Friends = async () => {
    const app_content = 
    `
    <div class="text-center">
        <h1>Friends Page</h1>
        <div id="friend-requests">
            <h2>Friend Requests</h2>
            <ul id="friend-requests-list">
                <li>Loading friend requests list..</li>
            </ul>
        </div>
        <div id="friends">
            <h2>Friends List</h2>
            <ul id="friends-list">
                <li>Loading friends list..</li>
            </ul>
        </div>
    </div>
    `;

    document.getElementById('app').innerHTML = app_content;

    const token = localStorage.getItem('auth_token');
    const friendsList = await fetch('/friend/friend_list/', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
            'Authorization': `Bearer ${token}`
        }
    });

    const friendsData = await friendsList.json();

    if (friendsList.status === 401 || friendsData.status === 0) {
        document.getElementById('app').innerHTML =  `
            <div class="text-center">
                <h1>Access Denied</h1>
                <p>You need to be logged in to view this page.</p>
            </div>
        `;
        return document.getElementById('app').innerHTML;
    }

    if (friendsData.friends.length === 0) {
        document.getElementById('friends').innerHTML = `
            <h2>Friends List</h2>
            <p>You have no friend. How sad :-( </p>
        `;
    } else {
        const friendsList = document.getElementById("friends-list");
        friendsList.innerHTML = '';

        friendsData.friends.forEach(friend => {
            const listItem = document.createElement("div");

            listItem.innerHTML = `
                ${friend.username} <img src="${friend.profile_picture}" alt="${friend.username}">
            `;

        friendsList.appendChild(listItem);
        });
    }

    const friendRequests = await fetch('/friend/friend_requests_list/', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
            'Authorization': `Bearer ${token}`
        }
    });

    const friendsRequestsData = await friendRequests.json();
    if (friendsRequestsData.friend_requests.length === 0) {
        document.getElementById('friend-requests').innerHTML = `
            <h2>Friend Requests</h2>
            <p>Nobody wants to be your friend.</p>
        `;
    } else {
        const friendRequestsList = document.getElementById("friend-requests-list");
        friendRequestsList.innerHTML = '';

        friendsRequestsData.friend_requests.forEach(friendRequest => {
            const listItem = document.createElement("div");
            listItem.innerHTML = `
                ${friendRequest.username} <img src="${friendRequest.profile_picture}" alt="${friendRequest.username}">
                <button class="btn btn-primary accept-request" data-relation-id="${friendRequest.id}">Accept</button>
                <button class="btn btn-danger decline-request" data-relation-id="${friendRequest.id}">Decline</button>
            `;

        friendRequestsList.appendChild(listItem);
        });

        document.querySelectorAll('.accept-request').forEach(button => {
            button.addEventListener('click', async (event) => {
                const requestId = event.target.getAttribute('data-relation-id');
                await handleFriendRequest('accept', requestId);
            });
        });

        document.querySelectorAll('.decline-request').forEach(button => {
            button.addEventListener('click', async (event) => {
                const requestId = event.target.getAttribute('data-relation-id');
                await handleFriendRequest('refuse', requestId);
            });
        });
    }
    return document.getElementById('app').innerHTML;
};

const handleFriendRequest = async (action, id) => {
    const token = localStorage.getItem('auth_token');
    const url = action === 'accept' 
        ? `/friend/accept_request/${id}/` 
        : `/friend/refuse_request/${id}/`;

    const response = await fetch(url, {
        method: 'POST',
        headers: {

            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
            'Authorization': `Bearer ${token}`
        }
    });

    if (response.ok) {
        await Friends();
    } else {
        alert('Failed to process the friend request.');
    }
};

const Stats = async () => {
    const token = localStorage.getItem('auth_token');

    // Render the basic structure of the Stats page
    const app_content = `
    <div class="text-center">
        <h1>Stats Page</h1>
        <div id="total-stats">
            <span id="total-stats-content">Loading total stats...</span>
        </div>
        <div id="game-history">
            <h2>Game History</h2>
            <ul id="game-history-list">
                <li>Loading game history...</li>
            </ul>
        </div>
    </div>
    `;

    document.getElementById('app').innerHTML = app_content;

    const statsResponse = await fetch('/stat/personal_stats/', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
            'Authorization': `Bearer ${token}`
        }
    });

    const statsData = await statsResponse.json();

    if (statsResponse.status === 401 ||statsData.status === 0) {
        document.getElementById('app').innerHTML = `
            <div class="text-center">
                <h1>Access Denied</h1>
                <p>You need to be logged in to view this page.</p>
            </div>
        `;
        return document.getElementById('app').innerHTML;
    }

    if (statsData.total_games === 0) {
        document.getElementById('app').innerHTML = `
        <div class="text-center">
            <h1>Stats Page</h1>
            <p>No games played yet.</p>
        </div>
        `;
    } else {
        document.getElementById("total-stats-content").textContent =
            `Total Games: ${statsData.total_games} | Win percentage: ${statsData.win_percentage}`;

        const gameHistoryList = document.getElementById("game-history-list");
        gameHistoryList.innerHTML = '';

        statsData.games.forEach(game => {
            const listItem = document.createElement("div");
            listItem.className = `game-stat ${game.is_winner ? 'victory' : 'defeat'}`;

            const resultText = game.is_winner ? 'Victory' : 'Defeat';
            listItem.innerHTML = `
                <strong>${resultText}</strong> -
                Opponent: ${game.opponent} |
                Your Score: ${game.personal_score} |
                Opponent's Score: ${game.opponent_score} |
                Duration: ${game.game_duration} |
                Date: ${new Date(game.game_date).toLocaleString()}
            `;

            gameHistoryList.appendChild(listItem);
        });
    }
    return document.getElementById('app').innerHTML;
};

const UserProfile = async (username) => {
    const token = localStorage.getItem('auth_token');

    const response = await fetch(`/users/get_profile/${username}/`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
            'Authorization': `Bearer ${token}`
        }
    });
    const data = await response.json();

    if (response.status === 401) {
        return `
            <div class="text-center">
                <h1>Access Denied</h1>
                <p>You need to be logged in to view this page.</p>
            </div>
        `;
    }

    if (response.status === 404) {
        console.log('User not found');
        return `
            <div class="text-center">
                <h1>User Not Found</h1>
                <p>The user ${username} does not exist.</p>
            </div>
        `;
    }

    const app_content = `
    <div class="text-center">
        <img src="${data.profile_picture}" alt="${data.username}" class="profile-picture-preview">
        <h1>${data.username}</h1>
        <div id="friendship"></div>
        <h2>Stats</h2>
        <div id="user-stats"> </div>
    `;
    
    document.getElementById('app').innerHTML = app_content;

    const userStats = document.getElementById('user-stats');
    const friendship = document.getElementById('friendship');
    friendship.innerHTML = get_friendship_content(data.friendship, data.id);

    if (data.stats.total_games === 0) {
        userStats.innerHTML = `
            <p>No games played yet.</p>
        `;
    }
    else {
        userStats.innerHTML = `
            <p>Total Games: ${data.stats.total_games} | Win percentage: ${data.stats.win_percentage}</p>
        `;
    }

    return document.getElementById('app').innerHTML;
};

function get_friendship_content(friendship_data, user_id) {
    // yourself: 0, not friend: 1, friend: 2, pending request: 3, request received: 4
    if (friendship_data.status === 2) {
        return `
            <p>Friend</p>
            <button class="btn btn-danger" id="remove-friend" data-relation-id=${friendship_data.id}>Remove Friend</button>
        `;
    } else if (friendship_data.status === 1) {
        return `
            <button class="btn btn-primary" id="add-friend" data-user-id=${user_id}>Add Friend</button>
        `;
    } else if (friendship_data.status === 3) {
        return `
            <p>Pending Request</p>
            <button class="btn btn-danger" id="cancel-request" data-relation-id=${friendship_data.id}>Cancel Request</button>
        `;
    } else if (friendship_data.status === 4) {
        return `
            <p>Friend Request Received</p>
            <button class="btn btn-primary accept-request" id="accept-request" data-relation-id=${friendship_data.id}>Accept</button>
            <button class="btn btn-danger decline-request" id="decline-request" data-relation-id=${friendship_data.id}>Decline</button>
        `;
    }
}

document.addEventListener("click", e => {
    if (e.target.matches("[data-link]")) {
        e.preventDefault();
        navigateTo(e.target.href);
    }
});

window.addEventListener("popstate", router);

document.addEventListener("DOMContentLoaded", router);
