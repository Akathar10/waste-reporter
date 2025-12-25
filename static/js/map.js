// Initialize Map
// Initialize Map
var map = L.map('map', {
    maxBounds: [[5.0, 65.0], [40.0, 100.0]], // Restrict to India Region
    maxBoundsViscosity: 1.0,
    minZoom: 4
}).setView([20.5937, 78.9629], 5); // Default center (India)

// Add Tile Layer (OpenStreetMap)
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Fetch Reports from API
fetch('/api/reports')
    .then(response => response.json())
    .then(data => {
        data.forEach(report => {
            // Skip invalid coordinates (0,0 is in the Atlantic Ocean)
            if (report.latitude == 0 && report.longitude == 0) return;

            var color = 'blue';
            if (report.severity === 'High') color = 'red';
            if (report.severity === 'Medium') color = 'orange';
            if (report.severity === 'Low') color = 'green';

            // Create a circle marker
            var marker = L.circleMarker([report.latitude, report.longitude], {
                color: color,
                fillColor: color,
                fillOpacity: 0.5,
                radius: 10
            }).addTo(map);

            marker.bindPopup(`
                <b>Status: ${report.status}</b><br>
                ${report.description}<br>
                <img src="/static/uploads/${report.image_path}" width="100px"><br>
                <a href="/status">Check Status ID: ${report.id}</a>
            `);
        });
    });