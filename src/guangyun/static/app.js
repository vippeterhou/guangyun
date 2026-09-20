const form = document.querySelector("#search-form");
const input = document.querySelector("#character-input");
const status = document.querySelector("#status");
const results = document.querySelector("#results");
const submitButton = form.querySelector("button");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderEntry(entry) {
  const original = entry.original_character
    ? `<p class="secondary">原字形：${escapeHtml(entry.original_character)}</p>`
    : "";
  const added = entry.is_added ? '<span class="tag">補錄</span>' : "";
  const converted = entry.matched_via
    ? `<span class="tag">${escapeHtml(entry.matched_via.input_character)} → ${escapeHtml(entry.matched_via.target_character)}</span>`
    : "";
  return `
    <article class="result-card">
      <div class="result-character">${escapeHtml(entry.character)}</div>
      <div>
        <div class="result-meta">
          <span class="tag">第${escapeHtml(entry.volume.order)}卷</span>
          <span class="tag">${escapeHtml(entry.volume.tone)}聲</span>
          <span class="tag">${escapeHtml(entry.rhyme.name)}韻</span>
          <span class="tag">${escapeHtml(entry.small_rhyme.head_character)}小韻</span>
          ${added}
          ${converted}
        </div>
        <p class="fanqie">${escapeHtml(entry.small_rhyme.fanqie)}</p>
        <p class="definition">${escapeHtml(entry.definition || "原書無注文")}</p>
        ${original}
      </div>
    </article>
  `;
}

async function searchCharacter(character) {
  submitButton.disabled = true;
  status.className = "status";
  status.textContent = "正在查詢…";
  results.replaceChildren();

  try {
    const response = await fetch(`/api/v1/characters?char=${encodeURIComponent(character)}`, {
      cache: "no-store",
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "查詢失敗");
    }
    if (payload.count === 0) {
      status.textContent = `《廣韻》中未找到「${character}」。`;
      return;
    }
    const resolvedCharacters = payload.resolved_characters ?? [];
    const resolution = resolvedCharacters.length
      ? `，並自動查詢繁體「${resolvedCharacters.join("、")}」`
      : "";
    status.textContent = `找到 ${payload.count} 條記錄${resolution}。`;
    results.innerHTML = payload.entries.map(renderEntry).join("");
    const url = new URL(window.location.href);
    url.searchParams.set("char", character);
    window.history.replaceState({}, "", url);
  } catch (error) {
    status.className = "status error";
    status.textContent = error.message;
  } finally {
    submitButton.disabled = false;
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const character = input.value.trim();
  if (character) {
    searchCharacter(character);
  }
});

const initialCharacter = new URLSearchParams(window.location.search).get("char");
if (initialCharacter) {
  input.value = initialCharacter;
  searchCharacter(initialCharacter);
}
