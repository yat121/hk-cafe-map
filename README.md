# HK Cafe Map

An interactive map of 27 specialty coffee cafes across Sai Ying Pun, HKU, and Kennedy Town in Hong Kong.

**Live Demo:** https://yat121.github.io/hk-cafe-map/

---

## Features

- **27 specialty coffee cafes** curated across Sai Ying Pun, HKU & Kennedy Town
- **Live busyness indicators** — 5 levels: Very Busy, Busy, Moderate, Quiet, Closed
- **Real photos** from Google Maps for each cafe
- **Operating hours** (where confirmed)
- **Google Maps ratings** displayed for each cafe
- **OpenRice links** (where available)
- **Multi-select filters** — filter by area and busyness level simultaneously
- **Interactive Leaflet map** with custom cafe markers
- **"Get Directions" button** — opens Google Maps app with directions to the cafe
- **Live HK clock** with busyness hint showing optimal visiting times
- **Responsive design** — works great on desktop and mobile

---

## How to Use

1. Open the [live demo](https://yat121.github.io/hk-cafe-map/) in your browser
2. Use the **filter panel** to narrow down cafes by area (SYP / HKU / K-Town) and busyness level
3. **Click a marker** on the map to see the cafe's details (rating, hours, photos, OpenRice link)
4. Click **"Get Directions"** to open Google Maps with turn-by-turn directions
5. Watch the **live HK clock** in the header — it will suggest the best times to visit based on current busyness

---

## Tech Stack

- **Single HTML file** with embedded CSS & JavaScript (no build step required)
- [Leaflet.js](https://leafletjs.com/) — interactive map
- [OpenStreetMap](https://www.openstreetmap.org/) — map tiles
- [Google Fonts](https://fonts.google.com/) — Playfair Display (headings) + Inter (body)

---

## Project Structure

| File | Description |
|------|-------------|
| `index.html` | The complete app — contains all CSS, JS, and cafe data inline |

> All cafe data, styles, and logic are embedded directly in `index.html`. To add or update a cafe, edit the `cafes` array near the top of the JavaScript section.

---

## How to Contribute / Update

The cafe data lives inside `index.html` as a JavaScript array. To add or edit a cafe:

1. Open `index.html`
2. Find the `cafes` array (near the top of the `<script>` section)
3. Add or update a cafe object with the following fields:

```javascript
{
  name: "Cafe Name",
  area: "SYP",          // "SYP" | "HKU" | "KTown"
  lat: 22.xxxx,
  lng: 114.xxxx,
  rating: 4.5,         // Google Maps rating
  reviewCount: 120,     // Number of reviews
  googleMapsUrl: "https://maps.google.com/...",
  openriceUrl: "https://www.openrice.com/...",  // optional
  hours: "08:00 - 18:00",  // optional
  photos: ["https://...jpg", "..."],   // Google Maps photo URLs
  busyness: "Moderate", // "Very Busy" | "Busy" | "Moderate" | "Quiet" | "Closed"
  busynessNote: "Usually quieter before 10am"
}
```

4. Commit and push your changes — GitHub Pages will auto-update
