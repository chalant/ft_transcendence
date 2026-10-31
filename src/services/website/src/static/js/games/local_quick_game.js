class LocalQuickGameState {
	constructor(context, game, prevState) {
		this.gameEndState = new GameEndedState(game, context, prevState, this);
		this.playingState = new PlayingState(game, context, this, this.gameEndState);
		this.game = game;
		this.prevState = prevState;
		this.context = context;
	}

	update(data) {
		const opponent1 = document.getElementById("opponent1");
		const opponent2 = document.getElementById("opponent2");

		if (data.type == "end") {
			this.gameStatus = "ended";
			opponent1.innerHTML = "";
			opponent2.innerHTML = "";
			this.gameEndState.setMessage(data.player_name);
			if (this.socket) {
				this.socket.close();
				this.socket = null;
			}
			this.context.canvas.style.display = "none";
			this.context.state = this.gameEndState;
			this.context.state.execute();
			return;
		}
		else if (data.type == "room.players") {
			opponent1.textContent = data.values.filter(player => player.player_position === 0)[0].player_name;
			opponent2.textContent = data.values.filter(player => player.player_position === 1)[0].player_name;

			if (this.game.name === "snake")
				opponent2.className = "text-success";
			else
				opponent2.className = "text-dark";
			return;
		}
		this.game.update(data);
	}

	handleEvent(event) {
		if (JSON.parse(event.data).status == "ready") {
			this.context.canvas.style.display = "";
			this.context.loadingOverlay.style.display = 'none';
			this.context.gameUI.style.display = 'none';
			this.context.changeState(this.playingState);
			this.game.start(this.socket);
		}
	}

	async startGame(player1, player2) {
		if (this.socket) {
			this.socket.close();
			this.socket = null;
		}
		try {
			const response1 = await fetch("/games/create_game/", {
				method: "POST",
				headers: {
					"X-CSRFToken": getCookie("csrftoken"),
					"Authorization": "Bearer " + localStorage.getItem("auth_token")
				},
				credentials: "include",
				body: JSON.stringify({
					"game": this.game.name,
					"mode": "local",
					"guest_name": player1
				})
			});

			if (!response1.ok) {
				throw new Error(`Error ${response1.status}: Failed to create game`);
			}

			const response2 = await fetch("/games/create_game/", {
				method: "POST",
				headers: {
					"X-CSRFToken": getCookie("csrftoken"),
					"Authorization": "Bearer " + localStorage.getItem("auth_token")
				},
				credentials: "include",
				body: JSON.stringify({
					"game": this.game.name,
					"mode": "local",
					"guest_name": player2
				})
			});

			if (!response2.ok) {
				throw new Error(`Error ${response2.status}: Failed to create game`);
			}
			const data = await response2.json();
			// make a single connection for both players.
			this.socket = new WebSocket(`wss://${data.ip_address}/ws/game/${this.game.name}/${data.game_room_id}/?csrf_token=${getCookie("csrftoken")}&token=${localStorage.getItem("auth_token")}&local=true&player1=${player1}&player2=${player2}`);
			if (this.socket.readyState > this.socket.OPEN) {
				this.cancel();
				throw new Error("WebSocket error: " + this.socket.readyState);
			}
			this.socket.addEventListener("open", () => {
				this.socket.addEventListener("message", (event) => {
					this.handleEvent(event);
				});
				this.playingState.bindSocket(this.socket);
			});
		}
		catch (error) {
			this.cancel();
		}
	}

	cancel() {
		this.context.state = this.prevState;
		this.context.state.execute();
	}

	execute() {
		this.context.gameUI.style.display = 'flex';
		this.context.gameMenu.style.display = 'flex';
		this.context.gameMenuHeader.textContent = `${this.game.name.toUpperCase()} LOCAL QUICK GAME`;
		this.context.gameMenuBody.innerHTML = `
		<form id="playerForm" class="d-flex flex-column justify-content-center">
			<h10 class="text-center mb-2">Room</h10>
			<input type="text" class="form-control custom-input text-light mb-2" id="player1" placeholder="Player 1 Name" required>
			<input type="text" class="form-control custom-input text-light" id="player2" placeholder="Player 2 Name" required>
		</form>`;
		this.context.gameMenuFooter.innerHTML = `
		<div class="d-flex flex-row justify-content-center align-items-center">
			<button type="button" id="playButton" class="btn btn-outline-light mx-2 w-100" disabled>Play</button>
			<button type="button" id="backButton" class="btn btn-outline-light w-100">Back</button>
		</div>
		`;
		// const grid = document.getElementById('game-room-grid');
		// grid.innerHTML += gameRoomForm;
		// grid.innerHTML += gameRoomForm;

		const player1Input = document.getElementById('player1');
		const player2Input = document.getElementById('player2');
		const playButton = document.getElementById('playButton');
		const backButton = document.getElementById('backButton');

		function checkPlayers() {
			if (player1Input.value.trim() !== '' && player2Input.value.trim() !== '') {
				playButton.disabled = false;
			}
			else {
				playButton.disabled = true;
			}
		}

		player1Input.addEventListener('input', checkPlayers);
		player2Input.addEventListener('input', checkPlayers);

		playButton.addEventListener('click', async () => {
			const player1 = player1Input.value.trim();
			const player2 = player2Input.value.trim();

			if (player1 && player2) {
				await this.startGame(player1, player2);
			}
		});
		backButton.addEventListener('click', () => this.cancel())
	}
}
