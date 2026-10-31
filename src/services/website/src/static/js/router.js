import { getCookie } from "./auth.js";

export const navigateTo = async url => {
	history.pushState(null, null, url);
	await router();
};

const router = async () => {
	const routes = [
		{ path: "/", view: Home },
		{ path: "/game", view: Games },
		{ path: "/settings", view: Settings },
		{ path: "/friends", view: Friends },
		{ path: "/stats", view: Stats },
		{ path: "/user/:username", view: UserProfile }
	];

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
	document.getElementById('app').innerHTML = await match.route.view(...params);

	if (match.route.path == "/game")
		window.dispatchEvent(new Event("game"));
};

const Home = () => `
	<div class="text-center">
		<h1>Home Page</h1>
		<p>Welcome to ft_transcendence!</p>
	</div>
`;

const Games = async () => {
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

	return `
	<div class="row">
		<div class="row justify-content-between align-items-center mb-2">
			<div class="col-4 text-start d-flex align-items-center">
				<span id="opponent1" class="text-dark"></span>
			</div>

			<div class="col-4 text-end d-flex justify-content-end align-items-center">
				<span id="opponent2" class="text-dark"></span>
			</div>
		</div>
		<div class="row text-center">
			<div class="canvas-container position-relative">
				<canvas id="gameCanvas2D" class="w-100 border"></canvas>
				<canvas id="gameCanvas3D" class="w-100 border"></canvas>
				<div id="disconnect-overlay" class="disconnect-overlay position-absolute top-0 start-0 w-100 h-100 flex-column align-items-center justify-content-center text-light" aria-hidden="true">
					<p id="disconnect-message" class="fs-4 mb-2"></p>
					<p class="mb-1">Waiting for reconnection. Game ends in</p>
					<span id="disconnect-countdown" class="display-3 fw-bold"></span>
				</div>
				<div id="game-ui" class="position-absolute top-0 start-0 w-100 h-100 flex-column align-items-center justify-content-center bg-dark">
					<div id="loading-overlay" class="loading-overlay position-absolute top-0 start-0 w-100 h-100 flex-column align-items-center justify-content-center bg-dark" aria-hidden="true">
						<div class="spinner"></div>
						<p class="text-light mt-3">Waiting for opponent...</p>
						<div id="overlay-body" class="text-center"></div>
					</div>
					<div id="game-menu" class="card position-absolute top-50 start-50 translate-middle bg-dark text-light" aria-hidden="true">
						<div id="game-menu-header" class="card-header d-flex flex-column justify-content-center align-items-center"></div>
						<div id="game-menu-body" class="card-body d-flex flex-column justify-content-center align-items-center"></div>
						<div id="game-menu-footer" class="card-footer d-flex flex-column justify-content-center align-items-center"></div>
					</div>
				</div>
			</div>
		</div>
		<div class="row mt-1 text-center">
		<div class="card players-container bg-dark text-center justify-content-center w-100 flex" id="playersContainer">
			<div id="players-container-header" class="card-header d-flex justify-content-center align-items-center">
				<h5 class="text-light mb-2 text-center">Participants</h5>
			</div>
			<div class="players-container bg-dark text-center justify-content-center w-100 d-flex" id="playersContainerBody"></div>
		</div>
		</div>
	</div>
	`;
}

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
				<button type="submit" class="btn btn-outline-success mt-2">Upload</button>
			</form>
		</div>

		<!-- Change Username -->
		<div id="username-change" class="mb-3">
			<h4>Change Username</h4>
			<form id="username-change-form">
				<input type="text" id="new-username" name="username" value="${username}" placeholder="New Username" required>
				<br>
				<button type="submit" class="btn btn-outline-success mt-2">Change Username</button>
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
				<button type="submit" class="btn btn-outline-success mt-2">Change Password</button>
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
			<h3>Friend Requests</h3>
			<ul id="friend-requests-list">
				<li>Loading friend requests list..</li>
			</ul>
		</div>
		<div id="friends">
			<h3>Friends List</h3>
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
			<h3>Friends List</h3>
			<p>You have no friend. How sad :-( </p>
		`;
	} else {
		const friendsList = document.getElementById("friends-list");
		friendsList.innerHTML = '';

		friendsData.friends.forEach(friend => {
			const listItem = document.createElement("div");

			listItem.innerHTML = `
				<div class="friend-item">
					<div class="friend-info">
						<div class="friend-picture-container">
							<a href="/user/${escapeHtml(friend.username)}" data-link>
								<img class="friend-picture" src="${escapeHtml(friend.profile_picture)}" alt="${escapeHtml(friend.username)}">
							</a>
					</div>
					<span class="friend-name">${escapeHtml(friend.username)}</span>
					<div class="online_status ${friend.is_online ? 'online' : 'offline'}"></div>
				</div>
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
			<h3>Friend Requests</h3>
			<p>Nobody wants to be your friend.</p>
		`;
	} else {
		const friendRequestsList = document.getElementById("friend-requests-list");
		friendRequestsList.innerHTML = '';

		friendsRequestsData.friend_requests.forEach(friendRequest => {
			const listItem = document.createElement("div");
			listItem.innerHTML = `
				<div class="friend-request-item">
					<div class="friend-info">
						<div class="friend-picture-container">
							<a href="/user/${escapeHtml(friendRequest.username)}" data-link>
								<img class="friend-picture" src="${escapeHtml(friendRequest.profile_picture)}" alt="${escapeHtml(friendRequest.username)}">
							</a>
						</div>
						<span class="friend-name">${escapeHtml(friendRequest.username)}</span>
					</div>
					<div class="friend-action-buttons">
						<button class="btn btn-outline-success" id="accept-request-list" data-relation-id="${friendRequest.id}">Accept</button>
						<button class="btn btn-outline-danger" id="decline-request-list" data-relation-id="${friendRequest.id}">Decline</button>
					</div>
				</div>
			`;
		friendRequestsList.appendChild(listItem);
		});
	}
	return document.getElementById('app').innerHTML;
};

const Stats = async () => {
	const token = localStorage.getItem('auth_token');

	const app_content = `
	<div class="container bg-light py-4">
		<div class="text-center">
			<h1 class="mb-4">Stats Page</h1>
			<div id="total-stats" class="mb-5 row d-flex justify-content-center">
				<div class="col-md-6" id="pong-stats">
					<p class="font-weight-bold text-primary">Loading pong stats...</p>
				</div>
				<div class="col-md-6" id="snake-stats">
					<p class="font-weight-bold text-primary">Loading snake stats...</p>
				</div>
			</div>
		</div>

		<div id="game-history" class="container mt-5">
			<h2 class="text-center mb-4">Game History</h2>
			<div class="row">
				<div class="col-md-6">
					<ul id="pong-history-list" class="list-group list-group-flush mb-5">
						<li class="list-group-item">Loading pong history...</li>
					</ul>
				</div>
				<div class="col-md-6">
					<ul id="snake-history-list" class="list-group list-group-flush">
						<li class="list-group-item">Loading snake history...</li>
					</ul>
				</div>
			</div>
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

	if (statsResponse.status === 401) {
		document.getElementById('app').innerHTML = `
			<div class="container text-center py-5">
				<h1>Access Denied</h1>
				<p>You need to be logged in to view this page.</p>
			</div>
		`;
		return document.getElementById('app').innerHTML;
	}

	updateGameStats('pong', statsData.pong);
	updateGameStats('snake', statsData.snake);

	return document.getElementById('app').innerHTML;
};

function updateGameStats(gameType, stats) {
	const statsContainer = document.getElementById(`${gameType}-stats`);
	const gameHistoryList = document.getElementById(`${gameType}-history-list`);

	if (stats && stats.total_games > 0) {
		statsContainer.innerHTML = `
		<div class="row d-flex justify-content-center">
			<h3 class="text-center">${gameType.charAt(0).toUpperCase() + gameType.slice(1)}</h3>
			<div class="col-md-6 card p-4 mx-2 mb-4 shadow-sm">
				<p class="h5"><strong>Total Games:</strong> ${stats.total_games}</p>
				<p class="h5"><strong>Average Score:</strong> ${stats.average_score}</p>
				<p class="h5"><strong>Total Playtime:</strong> ${stats.playtime}</p>
			</div>
			<div class="col-md-6 card p-4 mx-2 mb-4 shadow-sm">
				<p class="h5"><strong>Win Percentage:</strong> <span class="text-success fw-bold">${stats.win_percentage}%</span></p>
				${gameType === 'pong' ? `
					<p class="h5"><strong>Precision:</strong> <span class="text-primary fw-bold">${stats.precision}%</span></p>
				` : `
					<p class="h5"><strong>High Score:</strong> <span class="text-primary fw-bold">${stats.high_score}</span></p>
				`}
			</div>
			<div class="col-10 mt-3">
				<p class="mb-2">Win Percentage</p>
				<div class="progress">
					<div class="progress-bar bg-success" role="progressbar" style="width: ${stats.win_percentage}%;" aria-valuenow="${stats.win_percentage}" aria-valuemin="0" aria-valuemax="100">${stats.win_percentage}%</div>
				</div>
			</div>
			${gameType === 'pong' ? `
				<div class="col-10 mt-3">
					<p class="mb-2">Precision</p>
					<div class="progress">
						<div class="progress-bar bg-primary" role="progressbar" style="width: ${stats.precision}%;" aria-valuenow="${stats.precision}" aria-valuemin="0" aria-valuemax="100">${stats.precision}%</div>
					</div>
				</div>
			` : ''}
		</div>
		`;

		gameHistoryList.innerHTML = '';
		for (let i = stats.games.length - 1; i >= 0; i--) {
			const game = stats.games[i];
			const listItem = document.createElement("li");
			listItem.className = `list-group-item game-stat ${game.is_winner ? 'bg-success text-white' : 'bg-danger text-white'}`;

			const resultText = game.is_winner ? 'Victory' : 'Defeat';
			listItem.innerHTML = `
				<strong>${resultText}</strong> |
				Opponent: <a href="/user/${escapeHtml(game.opponent)}" class="text-white" data-link>${escapeHtml(game.opponent)}</a> |
				Score: ${game.personal_score} - ${game.opponent_score} |
				Duration: ${game.game_duration} |
				Date: ${new Date(game.game_date).toLocaleString()}
			`;

			gameHistoryList.appendChild(listItem);
		}
	} else {
		statsContainer.innerHTML = `
		<div class="row d-flex justify-content-center">
			<h3 class="text-center">${gameType.charAt(0).toUpperCase() + gameType.slice(1)}</h3>
			<div class="col-md-6 card p-4 mx-2 mb-4 shadow-sm">
				<p class="h5">No games played yet.</p>
			</div>
		</div>

		`;
		gameHistoryList.innerHTML = '<li class="list-group-item text-center bg-light">No games played yet.</li>';
	}
}

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
				<h2>Access Denied</h2>
				<p>You need to be logged in to view this page.</p>
			</div>
		`;
	}

	if (response.status === 404) {
		return `
			<div class="text-center">
				<h2>User Not Found</h2>
				<p>The user ${escapeHtml(username)} does not exist.</p>
			</div>
		`;
	}

	const app_content = `
	<div class="container text-center my-5">
		<img src="${escapeHtml(data.profile_picture)}" alt="${escapeHtml(data.username)}" class="rounded-circle mb-4 profile-picture-preview">
		<h1 class="fw-bold text-dark">${escapeHtml(data.username)}</h1>

		<div id="friendship" class="my-4"></div>

		<div class="container bg-light py-4">
			<div class="text-center">
				<h2 class="mb-4">Stats</h2>
				<div id="total-stats" class="mb-5 row d-flex justify-content-center">
					<div class="col-md-6" id="pong-stats">
						<p class="font-weight-bold text-primary">Loading pong stats...</p>
					</div>
					<div class="col-md-6" id="snake-stats">
						<p class="font-weight-bold text-primary">Loading snake stats...</p>
					</div>
				</div>
			</div>

			<div id="game-history" class="container mt-5">
				<h3 class="text-center mb-4">Game History</h3>
				<div class="row">
					<div class="col-md-6">
						<ul id="pong-history-list" class="list-group list-group-flush mb-5">
							<li class="list-group-item">Loading pong history...</li>
						</ul>
					</div>
					<div class="col-md-6">
						<ul id="snake-history-list" class="list-group list-group-flush">
							<li class="list-group-item">Loading snake history...</li>
						</ul>
					</div>
				</div>
			</div>
		</div>
	</div>
	`;

	document.getElementById('app').innerHTML = app_content;

	const friendship = document.getElementById('friendship');
	friendship.innerHTML = get_friendship_content(data.friendship, data.id);

	updateGameStats('pong', data.stats.pong);
	updateGameStats('snake', data.stats.snake);

	return document.getElementById('app').innerHTML;
};


function get_friendship_content(friendship_data, user_id) {
	// yourself: 0, not friend: 1, friend: 2, pending request: 3, request received: 4
	if (friendship_data.status === 2) {
		return `
			<p>You are friend already !</p>
			<button class="btn btn-outline-danger" id="remove-friend" data-relation-id=${friendship_data.id}>Remove Friend</button>
		`;
	} else if (friendship_data.status === 1) {
		return `
			<p>You are not friend !</p>
			<button class="btn btn-outline-success" id="add-friend" data-user-id=${user_id}>Add Friend</button>
		`;
	} else if (friendship_data.status === 3) {
		return `
			<p>You sent them a friend request !</p>
			<button class="btn btn-outline-danger" id="cancel-request" data-relation-id=${friendship_data.id}>Cancel Request</button>
		`;
	} else if (friendship_data.status === 4) {
		return `
			<p>They sen\'t you a friend request !</p>
			<button class="btn btn-outline-success accept-request" id="accept-request" data-relation-id=${friendship_data.id}>Accept</button>
			<button class="btn btn-outline-danger decline-request" id="decline-request" data-relation-id=${friendship_data.id}>Decline</button>
		`;
	} else {
		return '<p>Your profile</p>';
	}
}

document.addEventListener("click", e => {
	const link = e.target.closest("a[data-link]");
	if (link) {
		e.preventDefault();
		navigateTo(link.href);
	}
});

window.addEventListener("popstate", router);

document.addEventListener("DOMContentLoaded", router);

document.addEventListener("DOMContentLoaded", () => {
	document.addEventListener("click", async (event) => {
		if (event.target.matches("#accept-request-list")) {
			event.preventDefault();
			const relationId = event.target.getAttribute('data-relation-id');
			await handleAcceptRequest(relationId);
		}

		if (event.target.matches("#decline-request-list")) {
			event.preventDefault();
			const relationId = event.target.getAttribute('data-relation-id');
			await handleDeclineRequest(relationId);
		}

	});
});

async function handleAcceptRequest(relationId) {
	const token = localStorage.getItem('auth_token');
	const response = await fetch(`/friend/accept_friend/${relationId}/`, {
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
		alert('Failed to accept the request.');
	}
}

async function handleDeclineRequest(relationId) {
	const token = localStorage.getItem('auth_token');
	const response = await fetch(`/friend/decline_friend/${relationId}/`, {
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
		alert('Failed to decline the request.');
	}
}