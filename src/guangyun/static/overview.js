const statusElement = document.querySelector("#overview-status");
const contentElement = document.querySelector("#overview-content");
const canvas = document.querySelector("#fanqie-canvas");
const tooltip = document.querySelector("#network-tooltip");
const networkSummary = document.querySelector("#network-summary");
const networkSearchForm = document.querySelector("#network-search-form");
const networkSearchInput = document.querySelector("#network-search-input");
const networkFrequency = document.querySelector("#network-frequency");
const networkFrequencyValue = document.querySelector("#network-frequency-value");
const networkFocusControls = document.querySelector("#network-focus-controls");
const networkFocusLabel = document.querySelector("#network-focus-label");

const state = {
  overview: null,
  rhymeLayout: "source",
  selectedVolumeId: null,
  selectedRhymeId: null,
  network: null,
  networkMode: "global",
  visibleNetwork: { nodes: [], edges: [] },
  networkPositions: [],
  hoveredNetworkNode: null,
  networkFocusNode: null,
  networkFocusDepth: 1,
  networkMinFrequency: 1,
  networkTransform: { x: 0, y: 0, scale: 1 },
  networkDrag: null,
  networkDragMoved: false,
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
        duration: 880,
        delay: Math.min(index * 5, 280),
        easing: "cubic-bezier(0.22, 1, 0.36, 1)",
        fill: "backwards",
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

function networkRole(node) {
  if (node.upper_count > 0 && node.lower_count > 0) {
    return "both";
  }
  return node.upper_count > 0 ? "upper" : "lower";
}

function networkRoleLabel(node) {
  return {
    upper: "只作上字",
    lower: "只作下字",
    both: "上下皆用",
  }[networkRole(node)];
}

function buildAdjacency(edges) {
  const adjacency = new Map();
  edges.forEach((edge) => {
    if (!adjacency.has(edge.source)) {
      adjacency.set(edge.source, new Set());
    }
    if (!adjacency.has(edge.target)) {
      adjacency.set(edge.target, new Set());
    }
    adjacency.get(edge.source).add(edge.target);
    adjacency.get(edge.target).add(edge.source);
  });
  return adjacency;
}

function filteredNetwork() {
  const eligible = new Set(
    state.network.nodes
      .filter(
        (node) =>
          node.count >= state.networkMinFrequency || node.id === state.networkFocusNode,
      )
      .map((node) => node.id),
  );
  let edges = state.network.edges.filter(
    (edge) => eligible.has(edge.source) && eligible.has(edge.target),
  );
  let included = eligible;

  if (state.networkFocusNode) {
    const adjacency = buildAdjacency(edges);
    included = new Set([state.networkFocusNode]);
    let frontier = new Set([state.networkFocusNode]);
    for (let depth = 0; depth < state.networkFocusDepth; depth += 1) {
      const next = new Set();
      frontier.forEach((id) => {
        (adjacency.get(id) || []).forEach((neighbor) => {
          if (!included.has(neighbor)) {
            included.add(neighbor);
            next.add(neighbor);
          }
        });
      });
      frontier = next;
    }
    edges = edges.filter(
      (edge) => included.has(edge.source) && included.has(edge.target),
    );
  } else {
    const connected = new Set(edges.flatMap((edge) => [edge.source, edge.target]));
    included = new Set([...eligible].filter((id) => connected.has(id)));
  }

  return {
    nodes: state.network.nodes.filter((node) => included.has(node.id)),
    edges,
  };
}

function createNetworkPositions(network) {
  const bounds = canvas.getBoundingClientRect();
  const width = bounds.width;
  const height = bounds.height;
  const centerX = width / 2;
  const centerY = height / 2;
  const maximum = Math.max(1, ...network.nodes.map((node) => node.count));

  if (state.networkFocusNode) {
    const adjacency = buildAdjacency(network.edges);
    const distances = new Map([[state.networkFocusNode, 0]]);
    let frontier = [state.networkFocusNode];
    while (frontier.length) {
      const next = [];
      frontier.forEach((id) => {
        (adjacency.get(id) || []).forEach((neighbor) => {
          if (!distances.has(neighbor)) {
            distances.set(neighbor, distances.get(id) + 1);
            next.push(neighbor);
          }
        });
      });
      frontier = next;
    }
    const rings = new Map();
    network.nodes.forEach((node) => {
      const distance = distances.get(node.id) ?? state.networkFocusDepth;
      if (!rings.has(distance)) {
        rings.set(distance, []);
      }
      rings.get(distance).push(node);
    });
    const ringStep = Math.max(90, Math.min(width, height) * 0.28);
    return network.nodes.map((node) => {
      const distance = distances.get(node.id) ?? state.networkFocusDepth;
      const ring = rings.get(distance);
      const index = ring.findIndex((item) => item.id === node.id);
      const angle = distance === 0 ? 0 : (index / ring.length) * Math.PI * 2 - Math.PI / 2;
      const radius = distance * ringStep;
      return {
        ...node,
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius,
        radius:
          node.id === state.networkFocusNode
            ? 14
            : 4 + Math.sqrt(node.count / maximum) * 9,
      };
    });
  }

  const maximumRadius = Math.max(1, Math.min(width, height) * 0.44);
  const nodeRadii = network.nodes.map((node) =>
    state.networkMode === "core"
      ? 5 + Math.sqrt(node.count / maximum) * 13
      : 2 + Math.sqrt(node.count / maximum) * 7,
  );
  const centerGap =
    network.nodes.length > 1 ? nodeRadii[0] + nodeRadii[1] + 8 : 0;
  const outerRadius = Math.max(maximumRadius, centerGap);
  return network.nodes.map((node, index) => {
    const radius =
      index === 0
        ? 0
        : centerGap +
          (outerRadius - centerGap) *
            Math.sqrt((index - 1) / Math.max(1, network.nodes.length - 2));
    const angle = index * 2.399963229728653;
    return {
      ...node,
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
      radius: nodeRadii[index],
    };
  });
}

function updateNetworkSummary() {
  if (!state.network) {
    return;
  }
  const upper = state.visibleNetwork.nodes.filter((node) => node.upper_count > 0).length;
  const lower = state.visibleNetwork.nodes.filter((node) => node.lower_count > 0).length;
  const both = state.visibleNetwork.nodes.filter(
    (node) => node.upper_count > 0 && node.lower_count > 0,
  ).length;
  const filtered =
    state.visibleNetwork.nodes.length !== state.network.node_count ||
    state.networkFocusNode !== null;
  networkSummary.textContent = filtered
    ? `目前顯示 ${formatNumber(state.visibleNetwork.nodes.length)} 個字、${formatNumber(state.visibleNetwork.edges.length)} 種組合；上字 ${formatNumber(upper)}、下字 ${formatNumber(lower)}、上下皆用 ${formatNumber(both)}。`
    : `${formatNumber(state.network.node_count)} 個反切字、${formatNumber(state.network.edge_count)} 種組合；上字 ${formatNumber(upper)}、下字 ${formatNumber(lower)}、上下皆用 ${formatNumber(both)}。`;
}

function updateNetworkFocusControls() {
  const focused = state.networkFocusNode !== null;
  networkFocusControls.hidden = !focused;
  if (!focused) {
    return;
  }
  networkFocusLabel.textContent =
    `以「${state.networkFocusNode}」為中心，顯示${state.networkFocusDepth === 1 ? "一度" : "二度"}關係`;
  document.querySelectorAll("[data-network-depth]").forEach((button) => {
    button.classList.toggle(
      "is-active",
      Number(button.dataset.networkDepth) === state.networkFocusDepth,
    );
  });
}

function resetNetworkTransform() {
  state.networkTransform = { x: 0, y: 0, scale: 1 };
}

function fitNetworkView() {
  const bounds = canvas.getBoundingClientRect();
  if (!state.networkPositions.length || !bounds.width || !bounds.height) {
    resetNetworkTransform();
    drawNetwork();
    return;
  }
  const padding = 48;
  const xs = state.networkPositions.map((node) => node.x);
  const ys = state.networkPositions.map((node) => node.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const contentWidth = Math.max(1, maxX - minX);
  const contentHeight = Math.max(1, maxY - minY);
  const scale = Math.min(
    3,
    Math.max(
      0.28,
      Math.min(
        (bounds.width - padding * 2) / contentWidth,
        (bounds.height - padding * 2) / contentHeight,
      ),
    ),
  );
  state.networkTransform = {
    scale,
    x: bounds.width / 2 - ((minX + maxX) / 2) * scale,
    y: bounds.height / 2 - ((minY + maxY) / 2) * scale,
  };
  drawNetwork();
}

function rebuildNetworkView() {
  state.visibleNetwork = filteredNetwork();
  state.networkPositions = createNetworkPositions(state.visibleNetwork);
  updateNetworkSummary();
  updateNetworkFocusControls();
  fitNetworkView();
}

function resizeCanvas() {
  const ratio = window.devicePixelRatio || 1;
  const bounds = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, Math.round(bounds.width * ratio));
  canvas.height = Math.max(1, Math.round(bounds.height * ratio));
  canvas.getContext("2d").setTransform(ratio, 0, 0, ratio, 0, 0);
  if (state.network) {
    rebuildNetworkView();
  }
}

function connectedTo(id) {
  const connected = new Set([id]);
  state.visibleNetwork.edges.forEach((edge) => {
    if (edge.source === id) {
      connected.add(edge.target);
    }
    if (edge.target === id) {
      connected.add(edge.source);
    }
  });
  return connected;
}

function drawDirectionalEdge(context, source, target, highlighted) {
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const distance = Math.max(1, Math.hypot(dx, dy));
  const unitX = dx / distance;
  const unitY = dy / distance;
  const startX = source.x + unitX * (source.radius + 1);
  const startY = source.y + unitY * (source.radius + 1);
  const endX = target.x - unitX * (target.radius + 3);
  const endY = target.y - unitY * (target.radius + 3);
  context.beginPath();
  context.moveTo(startX, startY);
  context.lineTo(endX, endY);
  context.stroke();

  if (!highlighted && !state.networkFocusNode && state.networkTransform.scale < 2.2) {
    return;
  }
  const arrowSize = 4 / state.networkTransform.scale;
  const angle = Math.atan2(dy, dx);
  context.beginPath();
  context.moveTo(endX, endY);
  context.lineTo(
    endX - Math.cos(angle - Math.PI / 6) * arrowSize,
    endY - Math.sin(angle - Math.PI / 6) * arrowSize,
  );
  context.lineTo(
    endX - Math.cos(angle + Math.PI / 6) * arrowSize,
    endY - Math.sin(angle + Math.PI / 6) * arrowSize,
  );
  context.closePath();
  context.fill();
}

function drawNetwork() {
  if (!state.network) {
    return;
  }
  const context = canvas.getContext("2d");
  const bounds = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, bounds.width, bounds.height);
  context.save();
  context.translate(state.networkTransform.x, state.networkTransform.y);
  context.scale(state.networkTransform.scale, state.networkTransform.scale);
  const positions = new Map(state.networkPositions.map((node) => [node.id, node]));
  const highlightedId = state.hoveredNetworkNode || state.networkFocusNode;
  const highlightedNodes = highlightedId ? connectedTo(highlightedId) : null;
  const baseAlpha = state.networkMode === "core" ? 0.26 : 0.1;

  context.lineWidth =
    (state.networkMode === "core" ? 0.8 : 0.45) / state.networkTransform.scale;
  for (const edge of state.visibleNetwork.edges) {
    const source = positions.get(edge.source);
    const target = positions.get(edge.target);
    if (!source || !target) {
      continue;
    }
    const highlighted =
      highlightedId && (edge.source === highlightedId || edge.target === highlightedId);
    context.globalAlpha = highlighted ? 0.9 : highlightedId ? 0.045 : baseAlpha;
    context.strokeStyle = highlighted
      ? cssColor("--cp-network-upper")
      : cssColor("--cp-border-strong");
    context.fillStyle = context.strokeStyle;
    drawDirectionalEdge(context, source, target, highlighted);
  }

  const labelThreshold =
    state.networkPositions.length > 700 ? 2.8 : state.networkPositions.length > 250 ? 2.1 : 1.45;
  for (const node of state.networkPositions) {
    const related = !highlightedNodes || highlightedNodes.has(node.id);
    const role = networkRole(node);
    context.globalAlpha = related ? 0.96 : 0.16;
    context.fillStyle =
      role === "upper" ? cssColor("--cp-surface") : cssColor("--cp-network-lower");
    context.beginPath();
    context.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
    context.fill();

    if (role === "upper" || role === "both") {
      const ringWidth = Math.max(
        2.4 / state.networkTransform.scale,
        node.radius * 0.22,
      );
      context.globalAlpha = related ? 1 : 0.18;
      context.lineWidth = ringWidth;
      context.strokeStyle = cssColor("--cp-network-upper");
      context.beginPath();
      context.arc(
        node.x,
        node.y,
        Math.max(0.5, node.radius - ringWidth / 2),
        0,
        Math.PI * 2,
      );
      context.stroke();
    }

    const screenX = node.x * state.networkTransform.scale + state.networkTransform.x;
    const screenY = node.y * state.networkTransform.scale + state.networkTransform.y;
    const visible =
      screenX > -30 &&
      screenX < bounds.width + 30 &&
      screenY > -30 &&
      screenY < bounds.height + 30;
    const showLabel =
      visible &&
      (state.networkMode === "core" ||
        state.networkFocusNode ||
        (highlightedId && related) ||
        node.id === highlightedId ||
        state.networkTransform.scale >= labelThreshold);
    if (showLabel) {
      context.globalAlpha = 1;
      context.fillStyle = cssColor("--cp-text");
      const emphasized =
        node.id === highlightedId ||
        node.id === state.networkFocusNode;
      const fontSize = (emphasized ? 16 : 12) / state.networkTransform.scale;
      context.font = `${emphasized ? "700" : "500"} ${fontSize}px "Songti SC", "STSong", serif`;
      context.textAlign = "center";
      context.fillText(
        node.id,
        node.x,
        node.y - node.radius - 6 / state.networkTransform.scale,
      );
    }
  }
  context.globalAlpha = 1;
  context.restore();
}

function networkNodeAt(x, y) {
  const worldX = (x - state.networkTransform.x) / state.networkTransform.scale;
  const worldY = (y - state.networkTransform.y) / state.networkTransform.scale;
  let closest = null;
  let closestDistance = Infinity;
  for (const node of state.networkPositions) {
    const distance = Math.hypot(node.x - worldX, node.y - worldY);
    const hitRadius = Math.max(8 / state.networkTransform.scale, node.radius + 3);
    if (distance <= hitRadius && distance < closestDistance) {
      closest = node;
      closestDistance = distance;
    }
  }
  return closest;
}

async function loadNetwork(mode) {
  state.networkMode = mode;
  state.hoveredNetworkNode = null;
  state.networkFocusNode = null;
  state.networkFocusDepth = 1;
  state.networkMinFrequency = 1;
  networkFrequency.value = "1";
  networkFrequencyValue.textContent = "1";
  document.querySelectorAll("[data-network-mode]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.networkMode === mode);
    button.disabled = true;
  });
  state.network = await fetchJson(`/api/v1/overview/fanqie?mode=${mode}`);
  networkFrequency.max = String(
    Math.max(10, Math.min(40, Math.max(...state.network.nodes.map((node) => node.count)))),
  );
  document.querySelectorAll("[data-network-mode]").forEach((button) => {
    button.disabled = false;
  });
  resizeCanvas();
}

function focusNetworkNode(nodeId) {
  const node = state.network.nodes.find((item) => item.id === nodeId);
  if (!node) {
    return;
  }
  state.hoveredNetworkNode = null;
  state.networkFocusNode = node.id;
  state.networkFocusDepth = 1;
  rebuildNetworkView();
}

function zoomNetworkAt(screenX, screenY, requestedScale) {
  const oldScale = state.networkTransform.scale;
  const scale = Math.min(6, Math.max(0.28, requestedScale));
  const worldX = (screenX - state.networkTransform.x) / oldScale;
  const worldY = (screenY - state.networkTransform.y) / oldScale;
  state.networkTransform = {
    scale,
    x: screenX - worldX * scale,
    y: screenY - worldY * scale,
  };
  drawNetwork();
}

function bindPageSelectionEvents() {
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
      return;
    }
    const depthButton = event.target.closest("[data-network-depth]");
    if (depthButton && state.networkFocusNode) {
      state.networkFocusDepth = Number(depthButton.dataset.networkDepth);
      rebuildNetworkView();
    }
  });
}

function bindNetworkControlEvents() {
  networkSearchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const query = networkSearchInput.value.trim();
    if (!query) {
      networkSearchInput.setCustomValidity("請輸入一個反切字");
      networkSearchInput.reportValidity();
      return;
    }
    let node = state.network.nodes.find((item) => item.id === query);
    if (!node && state.networkMode === "core") {
      await loadNetwork("global");
      node = state.network.nodes.find((item) => item.id === query);
    }
    if (!node) {
      networkSearchInput.setCustomValidity("目前網絡中找不到這個反切字");
      networkSearchInput.reportValidity();
      return;
    }
    networkSearchInput.setCustomValidity("");
    state.networkMinFrequency = 1;
    networkFrequency.value = "1";
    networkFrequencyValue.textContent = "1";
    focusNetworkNode(node.id);
  });

  networkSearchInput.addEventListener("input", () => {
    networkSearchInput.setCustomValidity("");
  });

  networkFrequency.addEventListener("input", () => {
    state.networkMinFrequency = Number(networkFrequency.value);
    networkFrequencyValue.textContent = networkFrequency.value;
    rebuildNetworkView();
  });

  document.querySelector("#network-fit").addEventListener("click", fitNetworkView);
  document.querySelector("#network-reset").addEventListener("click", () => {
    resetNetworkTransform();
    drawNetwork();
  });
  document.querySelector("#network-return-global").addEventListener("click", () => {
    state.networkFocusNode = null;
    state.hoveredNetworkNode = null;
    rebuildNetworkView();
  });
}

function bindNetworkCanvasEvents() {
  canvas.addEventListener("pointerdown", (event) => {
    canvas.setPointerCapture(event.pointerId);
    state.networkDrag = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: state.networkTransform.x,
      originY: state.networkTransform.y,
    };
    state.networkDragMoved = false;
    canvas.style.cursor = "";
    canvas.classList.add("is-dragging");
  });

  canvas.addEventListener("pointermove", (event) => {
    if (state.networkDrag?.pointerId === event.pointerId) {
      const deltaX = event.clientX - state.networkDrag.startX;
      const deltaY = event.clientY - state.networkDrag.startY;
      if (Math.hypot(deltaX, deltaY) > 3) {
        state.networkDragMoved = true;
      }
      state.networkTransform.x = state.networkDrag.originX + deltaX;
      state.networkTransform.y = state.networkDrag.originY + deltaY;
      tooltip.hidden = true;
      drawNetwork();
      return;
    }
    const bounds = canvas.getBoundingClientRect();
    const node = networkNodeAt(event.clientX - bounds.left, event.clientY - bounds.top);
    const hoveredId = node?.id ?? null;
    if (hoveredId !== state.hoveredNetworkNode) {
      state.hoveredNetworkNode = hoveredId;
      drawNetwork();
    }
    if (!node) {
      tooltip.hidden = true;
      canvas.style.cursor = "";
      return;
    }
    canvas.style.cursor = "pointer";
    tooltip.hidden = false;
    tooltip.textContent =
      `${node.id} · ${networkRoleLabel(node)} · 上字 ${node.upper_count} · 下字 ${node.lower_count}`;
    tooltip.style.left = `${event.clientX - bounds.left + 12}px`;
    tooltip.style.top = `${event.clientY - bounds.top + 12}px`;
  });

  const endNetworkDrag = (event) => {
    if (state.networkDrag?.pointerId !== event.pointerId) {
      return;
    }
    if (canvas.hasPointerCapture(event.pointerId)) {
      canvas.releasePointerCapture(event.pointerId);
    }
    state.networkDrag = null;
    canvas.classList.remove("is-dragging");
  };

  canvas.addEventListener("pointerup", endNetworkDrag);
  canvas.addEventListener("pointercancel", endNetworkDrag);

  canvas.addEventListener("pointerleave", () => {
    tooltip.hidden = true;
    state.hoveredNetworkNode = null;
    canvas.style.cursor = "";
    if (!state.networkDrag) {
      drawNetwork();
    }
  });

  canvas.addEventListener("click", (event) => {
    if (state.networkDragMoved) {
      state.networkDragMoved = false;
      return;
    }
    const bounds = canvas.getBoundingClientRect();
    const node = networkNodeAt(event.clientX - bounds.left, event.clientY - bounds.top);
    if (node) {
      focusNetworkNode(node.id);
    }
  });

  canvas.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault();
      const bounds = canvas.getBoundingClientRect();
      const factor = event.deltaY < 0 ? 1.16 : 1 / 1.16;
      zoomNetworkAt(
        event.clientX - bounds.left,
        event.clientY - bounds.top,
        state.networkTransform.scale * factor,
      );
    },
    { passive: false },
  );

  canvas.addEventListener("keydown", (event) => {
    const bounds = canvas.getBoundingClientRect();
    if (event.key === "+" || event.key === "=") {
      event.preventDefault();
      zoomNetworkAt(bounds.width / 2, bounds.height / 2, state.networkTransform.scale * 1.2);
    } else if (event.key === "-") {
      event.preventDefault();
      zoomNetworkAt(bounds.width / 2, bounds.height / 2, state.networkTransform.scale / 1.2);
    } else if (event.key === "0") {
      event.preventDefault();
      fitNetworkView();
    } else if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) {
      event.preventDefault();
      const amount = 32;
      state.networkTransform.x +=
        event.key === "ArrowLeft" ? amount : event.key === "ArrowRight" ? -amount : 0;
      state.networkTransform.y +=
        event.key === "ArrowUp" ? amount : event.key === "ArrowDown" ? -amount : 0;
      drawNetwork();
    }
  });
}

function bindEvents() {
  bindPageSelectionEvents();
  bindNetworkControlEvents();
  bindNetworkCanvasEvents();
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
    await loadNetwork("global");
    statusElement.hidden = true;
    contentElement.hidden = false;
    requestAnimationFrame(resizeCanvas);
  } catch (error) {
    statusElement.className = "overview-status error";
    statusElement.textContent = error.message;
  }
}

initialize();
