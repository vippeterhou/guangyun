const form = document.querySelector("#search-form");
const input = document.querySelector("#character-input");
const status = document.querySelector("#status");
const results = document.querySelector("#results");
const submitButton = form.querySelector("button");
const wasedaImageBase =
  "https://archive.wul.waseda.ac.jp/kosho/ho04/ho04_01757";
const wasedaVolumePageCounts = {
  1: 72,
  2: 56,
  3: 58,
  4: 60,
  5: 59,
};
const chineseVolumeNumbers = {
  1: "一",
  2: "二",
  3: "三",
  4: "四",
  5: "五",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function wasedaImageUrl(volume, page) {
  const volumeToken = String(volume).padStart(4, "0");
  const pageToken = String(page).padStart(4, "0");
  const directory = `ho04_01757_${volumeToken}`;
  return `${wasedaImageBase}/${directory}/${directory}_p${pageToken}.jpg`;
}

function sourceScanLocation(sourceId) {
  const match = /^w([1-5])(\d{2})([ab])/.exec(sourceId ?? "");
  if (!match) {
    return null;
  }

  const volume = Number(match[1]);
  const leaf = Number(match[2]);
  const side = match[3];
  let page;

  // Each scan contains an open spread. Offsets account for the front matter
  // and the duplicate first opening in volume one.
  if (volume === 1) {
    if ((leaf === 7 && side === "b") || (leaf === 8 && side === "a")) {
      page = 15;
    } else {
      page = leaf + (side === "a" ? 8 : 9);
    }
  } else {
    const frontMatterOffset = volume === 4 ? 3 : 2;
    page = leaf + frontMatterOffset + (side === "b" ? 1 : 0);
  }

  const pageCount = wasedaVolumePageCounts[volume];
  if (page < 1 || page > pageCount) {
    return null;
  }
  return { volume, page, pageCount };
}

function renderSourceScan(entry, expanded) {
  const location = sourceScanLocation(entry.source_id);
  if (!location) {
    return "";
  }

  const volumeLabel = chineseVolumeNumbers[location.volume];
  const imageUrl = wasedaImageUrl(location.volume, location.page);
  const positionLabel = `卷${volumeLabel}・第${location.page}圖`;
  const imageAlt = `《廣韻》${positionLabel}書影`;

  return `
    <details
      class="source-scan"
      data-scan-details
      aria-label="${escapeHtml(entry.character)}的原書書影"
      ${expanded ? "open" : ""}
    >
      <summary class="source-scan-heading">
        <div>
          <p class="source-scan-kicker">澤存堂本原書</p>
          <h2 class="source-scan-title">書影</h2>
        </div>
      </summary>
      <div
        class="source-scan-content"
        data-scan-viewer
        data-volume="${location.volume}"
        data-page="${location.page}"
        data-page-count="${location.pageCount}"
      >
        <figure class="source-scan-frame">
          <a
            class="source-scan-image-link"
            data-scan-image-link
            href="${imageUrl}"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="在早稻田大學圖書館查看${positionLabel}完整影像"
          >
            <img
              class="source-scan-image"
              data-scan-image
              ${expanded ? `src="${imageUrl}"` : ""}
              alt="${imageAlt}"
              loading="lazy"
              decoding="async"
            >
          </a>
          <p class="source-scan-error" data-scan-error hidden>
            此頁原圖暫時無法載入；
            <a data-scan-error-link href="${imageUrl}" target="_blank" rel="noopener noreferrer">
              可直接前往早稻田原圖
            </a>。
          </p>
        </figure>
        <nav class="source-scan-controls" aria-label="原書書影翻頁">
          <button class="scan-nav-button" type="button" data-scan-action="last">末頁</button>
          <button class="scan-nav-button" type="button" data-scan-action="next">← 下一圖</button>
          <span class="source-scan-page" data-scan-page aria-live="polite">
            卷${volumeLabel} · 第 ${location.page} / ${location.pageCount} 圖
          </span>
          <button class="scan-nav-button" type="button" data-scan-action="previous">上一圖 →</button>
          <button class="scan-nav-button" type="button" data-scan-action="first">首頁</button>
        </nav>
      </div>
    </details>
  `;
}

function renderEntry(entry, scansExpanded) {
  const original = entry.original_character
    ? `<p class="secondary">原字形：${escapeHtml(entry.original_character)}</p>`
    : "";
  const added = entry.is_added ? '<span class="tag">補錄</span>' : "";
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
        </div>
        <p class="fanqie">${escapeHtml(entry.small_rhyme.fanqie)}</p>
        <p class="definition">${escapeHtml(entry.definition || "原書無注文")}</p>
        ${original}
      </div>
      ${renderSourceScan(entry, scansExpanded)}
    </article>
  `;
}

function updateScanViewer(viewer, requestedPage) {
  const volume = Number(viewer.dataset.volume);
  const pageCount = Number(viewer.dataset.pageCount);
  const page = Math.min(Math.max(requestedPage, 1), pageCount);
  const volumeLabel = chineseVolumeNumbers[volume];
  const positionLabel = `卷${volumeLabel}・第${page}圖`;
  const imageUrl = wasedaImageUrl(volume, page);
  const image = viewer.querySelector("[data-scan-image]");
  const imageLink = viewer.querySelector("[data-scan-image-link]");
  const error = viewer.querySelector("[data-scan-error]");
  const errorLink = viewer.querySelector("[data-scan-error-link]");

  viewer.dataset.page = String(page);
  image.hidden = false;
  image.src = imageUrl;
  image.alt = `《廣韻》${positionLabel}書影`;
  imageLink.href = imageUrl;
  imageLink.setAttribute(
    "aria-label",
    `在早稻田大學圖書館查看${positionLabel}完整影像`,
  );
  errorLink.href = imageUrl;
  viewer.querySelector("[data-scan-page]").textContent =
    `卷${volumeLabel} · 第 ${page} / ${pageCount} 圖`;
  error.hidden = true;

  viewer.querySelector('[data-scan-action="first"]').disabled = page === 1;
  viewer.querySelector('[data-scan-action="previous"]').disabled = page === 1;
  viewer.querySelector('[data-scan-action="next"]').disabled = page === pageCount;
  viewer.querySelector('[data-scan-action="last"]').disabled = page === pageCount;
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
    const hasMultipleEntries = payload.entries.length > 1;
    status.textContent = `找到 ${payload.count} 條記錄。`;
    results.innerHTML = payload.entries
      .map((entry) => renderEntry(entry, !hasMultipleEntries))
      .join("");
    results.querySelectorAll("[data-scan-details][open] [data-scan-viewer]").forEach((viewer) => {
      updateScanViewer(viewer, Number(viewer.dataset.page));
    });
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

results.addEventListener("click", (event) => {
  const button = event.target.closest("[data-scan-action]");
  if (!button || button.disabled) {
    return;
  }

  const viewer = button.closest("[data-scan-viewer]");
  const page = Number(viewer.dataset.page);
  const pageCount = Number(viewer.dataset.pageCount);
  const targetPage = {
    first: 1,
    previous: page - 1,
    next: page + 1,
    last: pageCount,
  }[button.dataset.scanAction];
  updateScanViewer(viewer, targetPage);
});

results.addEventListener(
  "toggle",
  (event) => {
    const details = event.target.closest("[data-scan-details]");
    if (!details) {
      return;
    }
    if (details.open) {
      const viewer = details.querySelector("[data-scan-viewer]");
      updateScanViewer(viewer, Number(viewer.dataset.page));
    }
  },
  true,
);

results.addEventListener(
  "error",
  (event) => {
    const image = event.target.closest("[data-scan-image]");
    if (!image) {
      return;
    }
    const viewer = image.closest("[data-scan-viewer]");
    image.hidden = true;
    viewer.querySelector("[data-scan-error]").hidden = false;
  },
  true,
);

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
