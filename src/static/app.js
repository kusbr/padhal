const state = {
  game: null,
  draftGuess: "",
};
const SESSION_GAME_KEY = "padhal_game_id";
const API_BASE_URL =
  window.location.port === "8080"
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : "";
let overlayTimerId = null;

const boardEl = document.getElementById("board");
const metaEl = document.getElementById("meta");
const overlayEl = document.getElementById("overlay");
const mobileInputEl = document.getElementById("mobile-input");
const newGameLinkEl = document.getElementById("new-game-link");

function showOverlay(text, isError = true) {
  if (!text) {
    overlayEl.textContent = "";
    overlayEl.classList.remove("visible", "error");
    return;
  }

  overlayEl.textContent = text;
  overlayEl.classList.toggle("error", isError);
  overlayEl.classList.add("visible");

  if (overlayTimerId) {
    clearTimeout(overlayTimerId);
  }

  overlayTimerId = window.setTimeout(() => {
    overlayEl.classList.remove("visible", "error");
  }, 2200);
}

function emptyBoard() {
  boardEl.innerHTML = "";
  for (let rowIndex = 0; rowIndex < 6; rowIndex += 1) {
    const row = document.createElement("div");
    row.className = "row";
    for (let colIndex = 0; colIndex < 5; colIndex += 1) {
      const tile = document.createElement("div");
      tile.className = "tile";
      row.appendChild(tile);
    }
    boardEl.appendChild(row);
  }
}

function renderBoard(game) {
  boardEl.innerHTML = "";
  for (let rowIndex = 0; rowIndex < game.max_guesses; rowIndex += 1) {
    const row = document.createElement("div");
    row.className = "row";
    const record = game.guesses[rowIndex];
    const isDraftRow = !record && game.status === "in_progress" && rowIndex === game.guess_count;

    for (let colIndex = 0; colIndex < game.word_length; colIndex += 1) {
      const tile = document.createElement("div");
      tile.className = "tile";
      if (record) {
        tile.textContent = record.guess[colIndex].toUpperCase();
        tile.classList.add(record.score[colIndex]);
      } else if (isDraftRow && state.draftGuess[colIndex]) {
        tile.textContent = state.draftGuess[colIndex].toUpperCase();
      }
      row.appendChild(tile);
    }
    boardEl.appendChild(row);
  }
}

function renderGame(game) {
  state.game = game;
  renderBoard(game);
  if (game.status !== "in_progress") {
    state.draftGuess = "";
    mobileInputEl.blur();
  } else {
    mobileInputEl.value = state.draftGuess;
  }

  if (game.status === "won") {
    showOverlay("Solved.", false);
  } else if (game.status === "lost") {
    showOverlay("Out of guesses.", true);
  }

  const details = [];
  if (game.answer) {
    details.push(`Answer: ${game.answer.toUpperCase()}`);
  }
  if (game.definition) {
    details.push(`Definition: ${game.definition}`);
  }
  metaEl.textContent = details.join("  ");
}

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed.");
  }
  return payload;
}

async function createGame() {
  showOverlay("");
  metaEl.textContent = "";

  try {
    const game = await requestJson("/api/games", {
      method: "POST",
      body: JSON.stringify({}),
    });
    sessionStorage.setItem(SESSION_GAME_KEY, game.game_id);
    state.draftGuess = "";
    renderGame(game);
  } catch (error) {
    emptyBoard();
    state.draftGuess = "";
    showOverlay(error.message, true);
  }
}

async function submitGuess() {
  if (!state.game) {
    showOverlay("Game is still loading.");
    return;
  }
  const guess = state.draftGuess.trim().toLowerCase();

  try {
    const game = await requestJson(`/api/games/${state.game.game_id}/guesses`, {
      method: "POST",
      body: JSON.stringify({ guess }),
    });
    state.draftGuess = "";
    mobileInputEl.value = "";
    renderGame(game);
  } catch (error) {
    showOverlay(error.message, true);
  }
}

function syncDraftFromInput() {
  let nextValue = mobileInputEl.value.toLowerCase().replace(/[^a-z]/g, "");
  if (nextValue.length > 5) {
    nextValue = nextValue.slice(0, 5);
  }
  if (nextValue !== state.draftGuess) {
    state.draftGuess = nextValue;
    if (state.game) {
      renderBoard(state.game);
    }
  }
  if (mobileInputEl.value !== nextValue) {
    mobileInputEl.value = nextValue;
  }
}

window.addEventListener("keydown", (event) => {
  if (!state.game || state.game.status !== "in_progress") {
    return;
  }

  if (document.activeElement === mobileInputEl) {
    return;
  }

  if (event.key === "Enter") {
    event.preventDefault();
    submitGuess();
    return;
  }

  if (event.key === "Backspace") {
    event.preventDefault();
    if (state.draftGuess.length > 0) {
      state.draftGuess = state.draftGuess.slice(0, -1);
      renderBoard(state.game);
    }
    return;
  }

  if (/^[a-zA-Z]$/.test(event.key) && state.draftGuess.length < 5) {
    state.draftGuess += event.key.toLowerCase();
    renderBoard(state.game);
  }
});

mobileInputEl.addEventListener("input", () => {
  syncDraftFromInput();
});

mobileInputEl.addEventListener("keydown", (event) => {
  if (!state.game || state.game.status !== "in_progress") {
    return;
  }
  if (event.key === "Enter") {
    event.preventDefault();
    submitGuess();
  }
});

boardEl.addEventListener("click", () => {
  if (state.game && state.game.status === "in_progress") {
    mobileInputEl.focus();
  }
});

newGameLinkEl.addEventListener("click", () => {
  createGame();
});

async function loadSessionGame() {
  const gameId = sessionStorage.getItem(SESSION_GAME_KEY);
  if (!gameId) {
    await createGame();
    return;
  }

  try {
    const game = await requestJson(`/api/games/${gameId}`);
    state.draftGuess = "";
    renderGame(game);
  } catch (error) {
    sessionStorage.removeItem(SESSION_GAME_KEY);
    await createGame();
  }
}

emptyBoard();
loadSessionGame();
