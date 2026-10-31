function escapeHtml(value) {
	return String(value).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}

class CustomGrid {
	constructor(col_size, id, spacing=null) {
		this.col_size = col_size;
		this.spacing = spacing;
		this.id = id
	}

	render(container) {
		container.innerHTML = `
		<div class="row w-100 h-100 justify-content-md-center" id=${this.id}></div>`;
	}

	addHTMLElement(value) {
		const container = document.getElementById(this.id);
		container.innerHTML += this.generateColumn(value);
	}

	generateColumn(value) {
		if (this.spacing) {
			return `
				<div class="col col-md-${this.col_size} ${this.spacing}">
					<div class="justify-content-center flex-column w-100 h-100">
						${value}
					</div>
				</div>`;
			}
		return `
			<div class="col col-md-${this.col_size}">
				<div class="justify-content-center flex-column w-100 h-100">
					${value}
				</div>
			</div>`;
	}
}

class PlayersGrid {
	constructor(context, container, col_size) {
		this.context = context;
		this.col_size = col_size;
		this.grid = new CustomGrid(col_size, "playersGrid", "mb-2")
		this.container = container;
	}

	render() {
		const body = document.getElementById("playersContainerBody");
		this.grid.render(body);
	}

	clear() {
		const body = document.getElementById("playersContainerBody");
		body.innerHTML = '';
		this.grid.render(body);
	}

	generatePlayer(player) {
		return `
		<div class="card text-center text-light player-card bg-dark">
			<h5 class="card-title text-light">${escapeHtml(player.player_name)}</h5>
		</div>`;
	}

	addPlayers(players) {
		this.clear();
		players.forEach(player => this.addPlayer(player));
	}

	addPlayer(player) {
		this.grid.addHTMLElement(this.generatePlayer(player))
	}
}
