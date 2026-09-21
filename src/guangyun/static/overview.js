const statusElement = document.querySelector("#overview-status");
const contentElement = document.querySelector("#overview-content");
const canvas = document.querySelector("#fanqie-canvas");
const tooltip = document.querySelector("#network-tooltip");
const networkDetail = document.querySelector("#network-detail");

const state = {
  overview: null,
  rhymeLayout: "source",
  selectedVolumeId: null,
  selectedRhymeId: null,
  network: null,
  networkMode: "core",
  networkPositions: [],
  selectedNetworkNode: null,
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatNumber(value) {
  return new Intl.NumberFormat("zh-Hant").format(value);
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "資料載入失敗");
  }
  return payload;
}

function renderMetrics() {
  const totals = state.overview.totals;
  const metrics = [
    ["卷", totals.volumes],
    ["韻", totals.rhymes],
    ["小韻", totals.small_rhymes],
    ["字條", totals.entries],
  ];
  document.querySelector("#metrics").innerHTML = metrics
    .map(
      ([label, value]) => `
        <article class="metric-card">
          <strong class="metric-value">${formatNumber(value)}</strong>
          <span class="metric-label">${label}</span>
        </article>
      `,
    )
    .join("");
}

function rhymesForVolume(volumeId) {
  return state.overview.rhymes.filter((rhyme) => rhyme.volume_id === volumeId);
}

function renderVolumeRibbons() {
  document.querySelector("#volume-ribbons").innerHTML = state.overview.volumes
    .map((volume) => {
      const rhymes = rhymesForVolume(volume.id);
      const segments = rhymes
        .map(
          (rhyme) => `
            <button
              type="button"
              class="ribbon-rhyme"
              style="flex-grow: ${rhyme.entry_count}"
              data-rhyme-id="${rhyme.id}"
              title="${escapeHtml(rhyme.name)}韻 · ${rhyme.small_rhyme_count} 小韻 · ${rhyme.entry_count} 字條"
              aria-label="${escapeHtml(rhyme.name)}韻，${rhyme.entry_count} 字條"
            ><span>${escapeHtml(rhyme.name)}</span></button>
          `,
        )
        .join("");
      return `
        <div class="volume-ribbon">
          <div class="volume-title">第${volume.order}卷 · ${escapeHtml(volume.tone)}聲</div>
          <div class="ribbon-track">${segments}</div>
          <div class="volume-summary">${volume.rhyme_count} 韻 · ${formatNumber(volume.entry_count)} 字條</div>
        </div>
      `;
    })
    .join("");
}

function renderRhymeMap() {
  const maximum = Math.max(...state.overview.rhymes.map((rhyme) => rhyme.entry_count));
  const toneHeaders = [
    ["平聲", "平"],
    ["上聲", "上"],
    ["去聲", "去"],
    ["入聲", "入"],
  ];
  const headers = toneHeaders
    .map(
      ([label, tone], index) => {
        const rhymeCount = state.overview.rhymes.filter((rhyme) => rhyme.tone === tone).length;
        return `
          <div class="tone-layout-label" style="grid-row: 1; grid-column: ${index + 1}">
            <strong>${label}</strong>
            <span>（${rhymeCount}韻）</span>
          </div>
        `;
      },
    )
    .join("");
  const placeholders = state.overview.tone_correspondence
    .flatMap((row, rowIndex) =>
      ["level", "rising", "departing", "entering"].flatMap((key, columnIndex) => {
        const item = row[key];
        if (item && !item.merged) {
          return [];
        }
        if (item?.merged) {
          const merged = item.merged;
          return [
            `
              <div
                class="tone-layout-placeholder is-merged"
                style="grid-row: ${rowIndex + 2}; grid-column: ${columnIndex + 1}"
              >
                <span>併入${escapeHtml(merged.rhyme_name)}韻<br>${escapeHtml(merged.head_character)}小韻</span>
              </div>
            `,
          ];
        }
        return [
          `<div class="tone-layout-placeholder" style="grid-row: ${rowIndex + 2}; grid-column: ${columnIndex + 1}">—</div>`,
        ];
      }),
    )
    .join("");
  const tiles = state.overview.rhymes
    .map((rhyme) => {
      const density = Math.max(8, Math.round((rhyme.entry_count / maximum) * 100));
      return `
        <button
          type="button"
          class="rhyme-tile"
          data-rhyme-id="${rhyme.id}"
          style="--density: ${density}%"
          title="${escapeHtml(rhyme.volume_title)} · ${rhyme.name}韻"
          aria-label="${escapeHtml(rhyme.name)}韻，${rhyme.small_rhyme_count} 小韻，${rhyme.entry_count} 字"
        >
          <span class="rhyme-density"></span>
          <span class="rhyme-name">${escapeHtml(rhyme.name)}</span>
          <span class="rhyme-stats">
            <span class="rhyme-stat">
              <strong>${rhyme.small_rhyme_count}</strong>
              <small>小韻</small>
            </span>
            <span class="rhyme-stat">
              <strong>${rhyme.entry_count}</strong>
              <small>字</small>
            </span>
          </span>
        </button>
      `;
    })
    .join("");
  document.querySelector("#rhyme-map").innerHTML = headers + placeholders + tiles;
  applyRhymeLayout(false);
}

function tonePositions() {
  const positions = new Map();
  state.overview.tone_correspondence.forEach((row, rowIndex) => {
    ["level", "rising", "departing", "entering"].forEach((key, columnIndex) => {
      const item = row[key];
      if (item && !item.merged) {
        positions.set(item.id, {
          row: rowIndex + 2,
          column: columnIndex + 1,
        });
      }
    });
  });
  return positions;
}

function applyRhymeLayout(animate = true) {
  const map = document.querySelector("#rhyme-map");
  const tiles = [...map.querySelectorAll(".rhyme-tile")];
  const first = new Map(tiles.map((tile) => [tile.dataset.rhymeId, tile.getBoundingClientRect()]));
  const positions = tonePositions();
  const toneLayout = state.rhymeLayout === "tones";

  map.classList.toggle("is-tone-layout", toneLayout);
  tiles.forEach((tile) => {
    const position = positions.get(Number(tile.dataset.rhymeId));
    tile.style.gridRow = toneLayout ? String(position.row) : "";
    tile.style.gridColumn = toneLayout ? String(position.column) : "";
  });

  document.querySelectorAll("[data-rhyme-layout]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.rhymeLayout === state.rhymeLayout);
  });
  document.querySelector("#rhyme-layout-note").textContent = toneLayout
    ? "「—」或併入說明表示該處未獨立立韻；點擊韻目方框可查看詳情。"
    : "方框中的刻度表示該韻收字密度；點擊可進入該韻。";

  if (!animate || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return;
  }

  const last = new Map(tiles.map((tile) => [tile.dataset.rhymeId, tile.getBoundingClientRect()]));
  tiles.forEach((tile, index) => {
    const before = first.get(tile.dataset.rhymeId);
    const after = last.get(tile.dataset.rhymeId);
    const deltaX = before.left - after.left;
    const deltaY = before.top - after.top;
    const scaleX = before.width / after.width;
    const scaleY = before.height / after.height;
    tile.animate(
      [
        {
          transform: `translate(${deltaX}px, ${deltaY}px) scale(${scaleX}, ${scaleY})`,
          transformOrigin: "top left",
        },
        { transform: "none", transformOrigin: "top left" },
      ],
      {
        duration: 680,
        delay: Math.min(index * 4, 220),
        easing: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
    );
  });
}

function renderVolumeChoices() {
  document.querySelector("#volume-list").innerHTML = state.overview.volumes
    .map(
      (volume) => `
        <button
          type="button"
          class="choice-button ${volume.id === state.selectedVolumeId ? "is-active" : ""}"
          data-volume-id="${volume.id}"
        >
          <span>第${volume.order}卷 · ${escapeHtml(volume.tone)}聲</span>
          <span class="choice-meta">${volume.rhyme_count} 韻</span>
        </button>
      `,
    )
    .join("");
}

function renderRhymeChoices() {
  const rhymes = rhymesForVolume(state.selectedVolumeId);
  document.querySelector("#rhyme-list").innerHTML = rhymes
    .map(
      (rhyme) => `
        <button
          type="button"
          class="choice-button ${rhyme.id === state.selectedRhymeId ? "is-active" : ""}"
          data-rhyme-id="${rhyme.id}"
        >
          <span>${escapeHtml(rhyme.name)}韻</span>
          <span class="choice-meta">${rhyme.small_rhyme_count} 小韻</span>
        </button>
      `,
    )
    .join("");
}

async function selectRhyme(rhymeId, scrollToHierarchy = false) {
  const rhyme = state.overview.rhymes.find((item) => item.id === rhymeId);
  if (!rhyme) {
    return;
  }
  state.selectedVolumeId = rhyme.volume_id;
  state.selectedRhymeId = rhyme.id;
  renderVolumeChoices();
  renderRhymeChoices();
  document.querySelector("#small-rhyme-list").innerHTML =
    '<p class="placeholder">正在載入小韻……</p>';
  const detail = await fetchJson(`/api/v1/rhymes/${rhyme.id}`);
  document.querySelector("#small-rhyme-list").innerHTML = detail.small_rhymes
    .map(
      (smallRhyme) => `
        <button
          type="button"
          class="choice-button"
          data-small-rhyme-id="${smallRhyme.id}"
        >
          <span>${escapeHtml(smallRhyme.head_character)} · ${escapeHtml(smallRhyme.primary_fanqie)}</span>
          <span class="choice-meta">${smallRhyme.entry_count} 字</span>
        </button>
      `,
    )
    .join("");
  document.querySelector("#hierarchy-detail").innerHTML = `
    <h3>${escapeHtml(detail.name)}韻</h3>
    <div class="detail-meta">
      <span class="detail-tag">${escapeHtml(detail.tone)}聲</span>
      <span class="detail-tag">${detail.small_rhyme_count} 小韻</span>
      <span class="detail-tag">${detail.entry_count} 字條</span>
    </div>
    <p class="placeholder">選擇左側小韻，即可查看其中全部同音字。</p>
  `;
  if (scrollToHierarchy) {
    document.querySelector("#hierarchy-title").scrollIntoView({ behavior: "smooth" });
  }
}

async function selectSmallRhyme(smallRhymeId) {
  document.querySelectorAll("[data-small-rhyme-id]").forEach((button) => {
    button.classList.toggle("is-active", Number(button.dataset.smallRhymeId) === smallRhymeId);
  });
  const detail = await fetchJson(`/api/v1/small-rhymes/${smallRhymeId}`);
  const characters = detail.entries
    .map(
      (entry) =>
        `<a href="/?char=${encodeURIComponent(entry.character)}" title="在查詢中打開">${escapeHtml(entry.character)}</a>`,
    )
    .join("");
  document.querySelector("#hierarchy-detail").innerHTML = `
    <h3>${escapeHtml(detail.head_character)}</h3>
    <div class="detail-meta">
      <span class="detail-tag">${escapeHtml(detail.fanqie)}</span>
      <span class="detail-tag">${escapeHtml(detail.rhyme.name)}韻</span>
      ${detail.ipa ? `<span class="detail-tag">${escapeHtml(detail.ipa)}</span>` : ""}
      <span class="detail-tag">${detail.entries.length} 字</span>
    </div>
    <p class="placeholder">點擊任一字，可返回主要查詢查看完整釋義。</p>
    <div class="character-cloud">${characters}</div>
  `;
}

function renderProfile() {
  const profile = state.overview.profile;
  const profileMetrics = [
    ["補錄字條", profile.added_entries],
    ["校改字頭", profile.corrected_headwords],
    ["原書異體標記", profile.glyph_variant_entries],
    ["IDS 字頭", profile.ids_headwords],
    ["擴展區字頭", profile.supplementary_headwords],
    ["私用區字頭", profile.private_use_headwords],
    ["含未識別字釋義", profile.unresolved_definition_entries],
    ["平均每小韻字數", profile.average_entries_per_small_rhyme],
  ];
  document.querySelector("#profile-metrics").innerHTML = profileMetrics
    .map(
      ([label, value]) => `
        <article class="profile-metric">
          <strong>${formatNumber(value)}</strong>
          <span>${label}</span>
        </article>
      `,
    )
    .join("");
  renderRankList(
    "#largest-rhymes",
    state.overview.largest_rhymes,
    (item) => `${item.name}韻`,
    (item) => item.entry_count,
  );
  renderRankList(
    "#largest-small-rhymes",
    state.overview.largest_small_rhymes,
    (item) => `${item.head_character} · ${item.primary_fanqie}`,
    (item) => item.entry_count,
  );
  renderRankList(
    "#fanqie-upper",
    state.overview.top_fanqie_upper,
    (item) => item.character,
    (item) => item.count,
  );
  renderRankList(
    "#fanqie-lower",
    state.overview.top_fanqie_lower,
    (item) => item.character,
    (item) => item.count,
  );
}

function renderRankList(selector, items, labelFor, valueFor) {
  const maximum = Math.max(...items.map(valueFor));
  document.querySelector(selector).innerHTML = items
    .map((item) => {
      const value = valueFor(item);
      const width = Math.max(4, Math.round((value / maximum) * 100));
      return `
        <div class="rank-row">
          <span class="rank-label">${escapeHtml(labelFor(item))}</span>
          <span class="rank-track"><span class="rank-bar" style="--rank-width: ${width}%"></span></span>
          <span class="rank-value">${formatNumber(value)}</span>
        </div>
      `;
    })
    .join("");
}

function cssColor(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function resizeCanvas() {
  const ratio = window.devicePixelRatio || 1;
  const bounds = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, Math.round(bounds.width * ratio));
  canvas.height = Math.max(1, Math.round(bounds.height * ratio));
  const context = canvas.getContext("2d");
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  drawNetwork();
}

function createNetworkPositions(network) {
  const bounds = canvas.getBoundingClientRect();
  const width = bounds.width;
  const height = bounds.height;
  const centerX = width / 2;
  const centerY = height / 2;
  const maximum = Math.max(...network.nodes.map((node) => node.count));
  const maximumRadius = Math.max(1, Math.min(width, height) * 0.44);
  const spacing = maximumRadius / Math.sqrt(Math.max(1, network.nodes.length - 1));
  return network.nodes.map((node, index) => {
    const radius = spacing * Math.sqrt(index);
    const angle = index * 2.399963229728653;
    return {
      ...node,
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
      radius: state.networkMode === "core"
        ? 5 + Math.sqrt(node.count / maximum) * 13
        : 2 + Math.sqrt(node.count / maximum) * 7,
    };
  });
}

function drawNetwork() {
  if (!state.network) {
    return;
  }
  const context = canvas.getContext("2d");
  const bounds = canvas.getBoundingClientRect();
  context.clearRect(0, 0, bounds.width, bounds.height);
  state.networkPositions = createNetworkPositions(state.network);
  const positions = new Map(state.networkPositions.map((node) => [node.id, node]));
  const selected = state.selectedNetworkNode;

  context.lineWidth = state.networkMode === "core" ? 0.8 : 0.35;
  context.strokeStyle = cssColor("--cp-border-strong");
  for (const edge of state.network.edges) {
    const source = positions.get(edge.source);
    const target = positions.get(edge.target);
    if (!source || !target) {
      continue;
    }
    const highlighted = selected && (edge.source === selected || edge.target === selected);
    context.globalAlpha = highlighted ? 0.9 : selected ? 0.08 : state.networkMode === "core" ? 0.3 : 0.12;
    context.strokeStyle = highlighted ? cssColor("--cp-accent") : cssColor("--cp-border-strong");
    context.beginPath();
    context.moveTo(source.x, source.y);
    context.lineTo(target.x, target.y);
    context.stroke();
  }

  for (const node of state.networkPositions) {
    const highlighted = !selected || node.id === selected;
    context.globalAlpha = highlighted ? 1 : 0.28;
    context.fillStyle = node.id === selected ? cssColor("--cp-accent") : cssColor("--cp-text");
    context.beginPath();
    context.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
    context.fill();
    if (state.networkMode === "core" || node.id === selected) {
      context.globalAlpha = 1;
      context.fillStyle = cssColor("--cp-text");
      context.font = node.id === selected
        ? '700 18px "Songti SC", "STSong", serif'
        : '13px "Songti SC", "STSong", serif';
      context.textAlign = "center";
      context.fillText(node.id, node.x, node.y - node.radius - 5);
    }
  }
  context.globalAlpha = 1;
}

function networkNodeAt(x, y) {
  let closest = null;
  let closestDistance = Infinity;
  for (const node of state.networkPositions) {
    const distance = Math.hypot(node.x - x, node.y - y);
    if (distance <= Math.max(8, node.radius + 3) && distance < closestDistance) {
      closest = node;
      closestDistance = distance;
    }
  }
  return closest;
}

function showNetworkNode(node) {
  const relatedEdges = state.network.edges
    .filter((edge) => edge.source === node.id || edge.target === node.id)
    .slice(0, 12);
  const examples = relatedEdges
    .flatMap((edge) =>
      edge.small_rhymes.slice(0, 2).map(
        (smallRhyme) => `
          <div class="network-detail-item">
            ${escapeHtml(edge.source)}${escapeHtml(edge.target)}切：
            ${escapeHtml(smallRhyme.head_character)}小韻 · ${escapeHtml(smallRhyme.rhyme_name)}韻
          </div>
        `,
      ),
    )
    .join("");
  networkDetail.innerHTML = `
    <h3>${escapeHtml(node.id)}</h3>
    <div class="detail-meta">
      <span class="detail-tag">上字 ${node.upper_count} 次</span>
      <span class="detail-tag">下字 ${node.lower_count} 次</span>
      <span class="detail-tag">合計 ${node.count} 次</span>
    </div>
    <div class="network-detail-list">${examples || '<p class="placeholder">沒有可顯示的組合。</p>'}</div>
  `;
}

async function loadNetwork(mode) {
  state.networkMode = mode;
  state.selectedNetworkNode = null;
  document.querySelectorAll("[data-network-mode]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.networkMode === mode);
    button.disabled = true;
  });
  networkDetail.innerHTML = '<p class="placeholder">正在整理反切關係……</p>';
  state.network = await fetchJson(`/api/v1/overview/fanqie?mode=${mode}`);
  const upperCharacterCount = state.network.nodes.filter((node) => node.upper_count > 0).length;
  const lowerCharacterCount = state.network.nodes.filter((node) => node.lower_count > 0).length;
  const bothCharacterCount = state.network.nodes.filter(
    (node) => node.upper_count > 0 && node.lower_count > 0,
  ).length;
  networkDetail.innerHTML = `
    <p class="placeholder">
      ${formatNumber(state.network.node_count)} 個反切字 ·
      ${formatNumber(state.network.edge_count)} 種組合。<br>
      反切上字 ${formatNumber(upperCharacterCount)} 個 ·
      反切下字 ${formatNumber(lowerCharacterCount)} 個 ·
      兼作上下字 ${formatNumber(bothCharacterCount)} 個。移動或點擊節點查看詳情。
    </p>
  `;
  document.querySelectorAll("[data-network-mode]").forEach((button) => {
    button.disabled = false;
  });
  resizeCanvas();
}

function bindEvents() {
  document.addEventListener("click", async (event) => {
    const volumeButton = event.target.closest("[data-volume-id]");
    if (volumeButton) {
      state.selectedVolumeId = Number(volumeButton.dataset.volumeId);
      const firstRhyme = rhymesForVolume(state.selectedVolumeId)[0];
      renderVolumeChoices();
      await selectRhyme(firstRhyme.id);
      return;
    }
    const rhymeButton = event.target.closest("[data-rhyme-id]");
    if (rhymeButton) {
      const isMapOrRibbon =
        rhymeButton.classList.contains("rhyme-tile") ||
        rhymeButton.classList.contains("ribbon-rhyme");
      await selectRhyme(Number(rhymeButton.dataset.rhymeId), isMapOrRibbon);
      return;
    }
    const layoutButton = event.target.closest("[data-rhyme-layout]");
    if (layoutButton && layoutButton.dataset.rhymeLayout !== state.rhymeLayout) {
      state.rhymeLayout = layoutButton.dataset.rhymeLayout;
      applyRhymeLayout();
      return;
    }
    const smallRhymeButton = event.target.closest("[data-small-rhyme-id]");
    if (smallRhymeButton) {
      await selectSmallRhyme(Number(smallRhymeButton.dataset.smallRhymeId));
      return;
    }
    const modeButton = event.target.closest("[data-network-mode]");
    if (modeButton && modeButton.dataset.networkMode !== state.networkMode) {
      await loadNetwork(modeButton.dataset.networkMode);
    }
  });

  canvas.addEventListener("mousemove", (event) => {
    const bounds = canvas.getBoundingClientRect();
    const node = networkNodeAt(event.clientX - bounds.left, event.clientY - bounds.top);
    if (!node) {
      tooltip.hidden = true;
      canvas.style.cursor = "default";
      return;
    }
    canvas.style.cursor = "pointer";
    tooltip.hidden = false;
    tooltip.textContent = `${node.id} · 上字 ${node.upper_count} · 下字 ${node.lower_count}`;
    tooltip.style.left = `${event.clientX - bounds.left + 12}px`;
    tooltip.style.top = `${event.clientY - bounds.top + 12}px`;
  });

  canvas.addEventListener("mouseleave", () => {
    tooltip.hidden = true;
    canvas.style.cursor = "default";
  });

  canvas.addEventListener("click", (event) => {
    const bounds = canvas.getBoundingClientRect();
    const node = networkNodeAt(event.clientX - bounds.left, event.clientY - bounds.top);
    state.selectedNetworkNode = node ? node.id : null;
    if (node) {
      showNetworkNode(node);
    }
    drawNetwork();
  });

  window.addEventListener("resize", resizeCanvas);
}

async function initialize() {
  bindEvents();
  try {
    state.overview = await fetchJson("/api/v1/overview");
    renderMetrics();
    renderVolumeRibbons();
    renderRhymeMap();
    renderProfile();
    state.selectedVolumeId = state.overview.volumes[0].id;
    renderVolumeChoices();
    await selectRhyme(rhymesForVolume(state.selectedVolumeId)[0].id);
    await loadNetwork("core");
    statusElement.hidden = true;
    contentElement.hidden = false;
    requestAnimationFrame(resizeCanvas);
  } catch (error) {
    statusElement.className = "overview-status error";
    statusElement.textContent = error.message;
  }
}

initialize();
