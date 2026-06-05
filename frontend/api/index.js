const express = require("express");
const bodyParser = require("body-parser");
const axios = require("axios");

const app = express();
const BACKEND_URL = process.env.BACKEND_URL || "https://solariq-backend.vercel.app";

const dashboardUser = {
  username: "ABC&D Block",
  latitude: "",
  longitude: "",
  avg_power: 170,
};

// Middleware
app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());
app.set("view engine", "ejs");
app.set("views", "../views");

// Routes
app.get("/", async (req, res) => {
  try {
    const [todayRes, historyRes] = await Promise.all([
      axios.get(`${BACKEND_URL}/today_status`),
      axios.get(`${BACKEND_URL}/history`),
    ]);

    res.render("dashboard", {
      user: dashboardUser,
      avg_power: dashboardUser.avg_power,
      todayData: todayRes.data || null,
      historyData: historyRes.data || [],
      forecastData: [],
    });
  } catch (err) {
    console.error("❌ Backend connection error:", err.message);
    res.render("dashboard", {
      user: dashboardUser,
      avg_power: dashboardUser.avg_power,
      todayData: null,
      historyData: [],
      forecastData: [],
      error: "Unable to connect to backend",
    });
  }
});

app.post("/profile/update", async (req, res) => {
  try {
    const { latitude, longitude, avg_power } = req.body;

    const lat = latitude !== undefined ? Number(latitude) : undefined;
    const lon = longitude !== undefined ? Number(longitude) : undefined;
    const avg = avg_power !== undefined ? Number(avg_power) : undefined;

    const update = {};
    if (!Number.isNaN(lat)) update.latitude = lat;
    if (!Number.isNaN(lon)) update.longitude = lon;
    if (!Number.isNaN(avg)) update.avg_power = avg;

    if (Object.keys(update).length === 0) {
      return res.status(400).json({ status: "error", message: "No valid fields provided" });
    }

    Object.assign(dashboardUser, update);
    return res.json({ status: "success", user: dashboardUser });
  } catch (err) {
    console.error("Profile update error:", err);
    return res.status(500).json({ status: "error", message: "Server error" });
  }
});

module.exports = app;
