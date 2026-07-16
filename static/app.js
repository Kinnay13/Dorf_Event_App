const eventList = document.querySelector("#eventList");
const eventCount = document.querySelector("#eventCount");
const hotspotCount = document.querySelector("#hotspotCount");
const searchInput = document.querySelector("#searchInput");
const categoryFilter = document.querySelector("#categoryFilter");
const segmentButtons = [...document.querySelectorAll(".segment")];

let activeTimeframe = "all";
let events = [];
let markers = new Map();

const map = L.map("map", {
  zoomControl: true,
  scrollWheelZoom: true
}).setView([49.505, 10.418], 14);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap"
}).addTo(map);

const markerIcon = L.divIcon({
  className: "event-marker",
  html: "<span></span>",
  iconSize: [24, 24],
  iconAnchor: [12, 12]
});

const style = document.createElement("style");
style.textContent = `
  .event-marker span {
    display: block;
    width: 22px;
    height: 22px;
    border: 3px solid #fff;
    border-radius: 50%;
    background: #2f7d46;
    box-shadow: 0 8px 18px rgba(23, 33, 27, 0.28);
  }
`;
document.head.appendChild(style);

async function fetchEvents() {
  const params = new URLSearchParams({
    category: categoryFilter.value,
    timeframe: activeTimeframe,
    search: searchInput.value.trim()
  });
  const response = await fetch(`/api/events?${params}`);
  events = await response.json();
  render();
}

function render() {
  renderSummary();
  renderMarkers();
  renderEventList();
}

function renderSummary() {
  const totalInterest = events.reduce((sum, event) => sum + event.interested_count, 0);
  eventCount.textContent = `${events.length} ${events.length === 1 ? "Event" : "Events"}`;
  hotspotCount.textContent = `${totalInterest} Zusagen`;
}

function renderMarkers() {
  markers.forEach((marker) => marker.remove());
  markers = new Map();

  const bounds = [];
  events.forEach((event) => {
    const marker = L.marker([event.lat, event.lng], { icon: markerIcon })
      .addTo(map)
      .bindPopup(`
        <p class="popup-title">${event.title}</p>
        <p class="popup-meta">${event.time_label}<br>${event.location}</p>
      `);

    marker.on("click", () => focusEvent(event.id));
    markers.set(event.id, marker);
    bounds.push([event.lat, event.lng]);
  });

  if (bounds.length > 0) {
    map.fitBounds(bounds, { padding: [42, 42], maxZoom: 15 });
  }
}

function renderEventList() {
  if (events.length === 0) {
    eventList.innerHTML = `<article class="event-card"><h2>Keine Events gefunden</h2><p class="description">Passe Suche oder Filter an.</p></article>`;
    return;
  }

  eventList.innerHTML = events.map((event) => `
    <article class="event-card" id="card-${event.id}">
      <div class="event-topline">
        <span class="category" data-category="${event.category}">${event.category}</span>
        <span class="interest-count">${event.interested_count} interessiert</span>
      </div>
      <h2>${event.title}</h2>
      <p class="meta">${event.time_label} · ${event.location}</p>
      <p class="description">${event.description}</p>
      <p class="verified">${event.verified ? "Verifizierter Veranstalter" : "Noch nicht verifiziert"} · ${event.organization}</p>
      <div class="card-actions">
        <span>${event.address}</span>
        <button class="interest-button" data-interest="${event.id}">Interesse</button>
      </div>
    </article>
  `).join("");

  document.querySelectorAll("[data-interest]").forEach((button) => {
    button.addEventListener("click", () => markInterest(button.dataset.interest));
  });

  document.querySelectorAll(".event-card").forEach((card) => {
    card.addEventListener("mouseenter", () => {
      const id = card.id.replace("card-", "");
      markers.get(id)?.openPopup();
    });
  });
}

function focusEvent(id) {
  document.querySelectorAll(".event-card").forEach((card) => card.classList.remove("active"));
  const card = document.querySelector(`#card-${CSS.escape(id)}`);
  if (card) {
    card.classList.add("active");
    card.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
}

async function markInterest(id) {
  const response = await fetch(`/api/events/${id}/interest`, { method: "POST" });
  const updatedEvent = await response.json();
  events = events.map((event) => event.id === updatedEvent.id ? updatedEvent : event);
  render();
  markers.get(id)?.openPopup();
  focusEvent(id);
}

let searchTimer = 0;
searchInput.addEventListener("input", () => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(fetchEvents, 180);
});

categoryFilter.addEventListener("change", fetchEvents);

segmentButtons.forEach((button) => {
  button.addEventListener("click", () => {
    segmentButtons.forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    activeTimeframe = button.dataset.timeframe;
    fetchEvents();
  });
});

fetchEvents();

