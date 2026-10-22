#!/usr/bin/env node
/*
 * Expeditions: the computed sky for every dated expedition, one sky per candidate lunation.
 *
 *   node expeditions/compile/sky.cjs <hygdata_v41.csv> <astronomy-engine dir>
 *     writes expeditions/build/sky/<slug>.json and expeditions/build/sky/stars.json
 *
 * COMPUTED, never attested. The text gives a lunar date (and sometimes a weekday); it never
 * gives a Julian date. Which lunation a month of 0-3 AH fell in is a question for the scholars
 * (intercalation before 10 AH), so three candidates are computed: the lunation the modern
 * tabular calendar points to, and the one before and after it. A month begins on the first
 * evening the Moon is 30 hours past conjunction and 8 degrees up at sunset: a stated stand-in
 * for sighting the crescent, not a visibility model.
 * Sources: astronomy-engine 2.1.19 (MIT); HYG v4.1 (CC BY-SA 4.0).
 */
const fs = require('fs');
const path = require('path');
const [csvPath, aeDir] = process.argv.slice(2);
if (!csvPath || !aeDir) { console.error('usage: sky.cjs <hyg.csv> <astronomy-engine dir>'); process.exit(2); }
const A = require(path.resolve(aeDir));
const ROOT = path.resolve(__dirname, '..');
const DEFS = JSON.parse(fs.readFileSync(path.join(ROOT, 'defs', 'expeditions.json'), 'utf8'));
const OUT = path.join(ROOT, 'build', 'sky');
fs.mkdirSync(OUT, { recursive: true });

const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const CRESCENT_RULE = 'A month begins the first evening the Moon is 30 hours past conjunction and 8 degrees above the horizon at sunset: a simple stand-in for sighting the crescent.';

const dateOfJd = jd => new Date((jd - 2440587.5) * 86400000);
function julianOf(t) {
  const jd = t.ut + 2451545.0, Z = Math.floor(jd + 0.5), F = jd + 0.5 - Z;
  const B = Z + 1524, C = Math.floor((B - 122.1) / 365.25), D = Math.floor(365.25 * C), E = Math.floor((B - D) / 30.6001);
  const d = Math.floor(B - D - Math.floor(30.6001 * E) + F), m = E < 14 ? E - 1 : E - 13, y = m > 2 ? C - 4716 : C - 4715;
  return { y, m, d, weekday: DAYS[(Math.floor(jd + 0.5) + 1) % 7] };
}
// The weekday and Julian date of the civil day that contains local noon after time t.
const fmt = j => `${j.weekday} ${j.d} ${MONTHS[j.m - 1]} ${j.y}`;
// Modern tabular (civil) Islamic calendar, epoch 16 July 622 Julian: a reference point only.
const tabularJd = (y, m, d) => d + Math.ceil(29.5 * (m - 1)) + (y - 1) * 354 + Math.floor((3 + 11 * y) / 30) + 1948439.5 - 1;

function altaz(body, t, obs) {
  const e = A.Equator(body, t, obs, true, true), h = A.Horizon(t, obs, e.ra, e.dec, 'normal');
  return [+h.altitude.toFixed(2), +h.azimuth.toFixed(2)];
}

function lunation(conj, obs, day, scene, offMin) {
  let ss = A.SearchRiseSet(A.Body.Sun, obs, -1, conj, 3);
  for (;;) {
    const age = (ss.ut - conj.ut) * 24, alt = altaz(A.Body.Moon, ss, obs)[0];
    if (age >= 30 && alt >= 8) break;
    ss = A.SearchRiseSet(A.Body.Sun, obs, -1, ss.AddDays(0.5), 3);
  }
  const crescentEve = ss;
  // The evening that begins day N is N-1 evenings after the crescent evening.
  const eveN = A.SearchRiseSet(A.Body.Sun, obs, -1, crescentEve.AddDays(day - 1 - 0.5), 3);
  const dawnN = A.SearchRiseSet(A.Body.Sun, obs, +1, eveN, 1);              // sunrise of day N
  const noonN = A.SearchHourAngle(A.Body.Sun, obs, 0, dawnN, +1);           // local noon of day N
  const sunsetN = A.SearchRiseSet(A.Body.Sun, obs, -1, dawnN, 1);           // sunset ending day N
  const dawnN1 = A.SearchRiseSet(A.Body.Sun, obs, +1, sunsetN, 1);
  let from, to;
  if (scene === 'eve-to-noon') { from = eveN.AddDays(-0.5 / 24); to = noonN.time.AddDays(0.25 / 24); }
  else if (scene === 'forenoon') { from = dawnN.AddDays(-0.75 / 24); to = noonN.time.AddDays(0.5 / 24); }
  else if (scene === 'night-after') { from = sunsetN.AddDays(-0.5 / 24); to = dawnN1.AddDays(0.5 / 24); }
  const frames = [];
  for (let t = from; t.ut <= to.ut; t = t.AddDays(15 / 1440)) {
    frames.push({ ut: t.date.toISOString().slice(11, 16), lst: +(A.SiderealTime(t) * 15 + obs.longitude).toFixed(3),
      moon: altaz(A.Body.Moon, t, obs), sun: altaz(A.Body.Sun, t, obs) });
  }
  const dayOf = julianOf(noonN.time);
  const ref = scene === 'night-after' ? sunsetN.AddDays(2 / 24) : eveN.AddDays(2 / 24);
  const ill = A.Illumination(A.Body.Moon, ref);
  const out = {
    conjunction: fmt(julianOf(conj)),
    crescent_evening: fmt(julianOf(crescentEve)),
    day: fmt(dayOf),
    weekday: dayOf.weekday,
    moon_illuminated_pct: +(ill.phase_fraction * 100).toFixed(1),
    local_offset_minutes: offMin,
    sunset_ut: (scene === 'night-after' ? sunsetN : eveN).date.toISOString().slice(11, 16),
    frames,
  };
  if (scene === 'forenoon') {
    // When the Sun stands at 90% of its noon altitude ("had nearly reached its height").
    const top = altaz(A.Body.Sun, noonN.time, obs)[0];
    let t = dawnN; while (altaz(A.Body.Sun, t, obs)[0] < 0.9 * top) t = t.AddDays(5 / 1440);
    out.sun_noon_altitude = top; out.sun_near_height_ut = t.date.toISOString().slice(11, 16);
  }
  if (scene === 'night-after') {
    const len = dawnN1.ut - sunsetN.ut;
    out.night_hours = +(len * 24).toFixed(2);
    out.moment_ut = sunsetN.AddDays(len / 3).date.toISOString().slice(11, 16);
    out.moment_moon = altaz(A.Body.Moon, sunsetN.AddDays(len / 3), obs);
    const ms = A.SearchRiseSet(A.Body.Moon, obs, -1, sunsetN, 1);
    out.moonset_ut = ms ? ms.date.toISOString().slice(11, 16) : null;
  } else {
    const mr = A.SearchRiseSet(A.Body.Moon, obs, +1, eveN.AddDays(-0.2), 1.2);
    out.moonrise_minutes_after_sunset = mr ? Math.round((mr.ut - eveN.ut) * 1440) : null;
  }
  return out;
}

for (const x of DEFS.expeditions) {
  if (!x.date) continue;
  const p = DEFS.places[x.anchor];
  const obs = new A.Observer(p.lat, p.lon, 50);
  const { year, month, day } = x.date.hijri;
  const tab = tabularJd(year, month, day);
  // the conjunction before the tabular first of the month, then one lunation either side
  const first = A.MakeTime(dateOfJd(tab - day + 1));
  const conj0 = A.SearchMoonPhase(0, first.AddDays(-20), 25);
  const conjs = [A.SearchMoonPhase(0, conj0.AddDays(-35), 10), conj0, A.SearchMoonPhase(0, conj0.AddDays(20), 15)];
  const candidates = conjs.map((c, i) => ({ key: ['before', 'tabular', 'after'][i], ...lunation(c, obs, day, x.date.scene, Math.round(p.lon * 4)) }));
  const tj = julianOf(A.MakeTime(dateOfJd(tab + 0.5)));
  const data = { slug: x.slug, place: p, scene: x.date.scene, tabular: fmt(tj), crescent_rule: CRESCENT_RULE,
    method: 'astronomy-engine 2.1.19 (MIT); stars from HYG v4.1 (CC BY-SA 4.0); times UT, shown as local solar time', candidates };
  fs.writeFileSync(path.join(OUT, `${x.slug}.json`), JSON.stringify(data));
  console.log(x.slug, 'tabular', data.tabular, '|', candidates.map(c => `${c.key}: ${c.day}`).join(' | '));
}

// Stars to magnitude 4.9: proper motion back to 624 CE, precessed to date (one set serves 621-625 CE).
const rows = fs.readFileSync(csvPath, 'utf8').split('\n');
const head = rows[0].split(',').map(s => s.replace(/"/g, ''));
const ix = k => head.indexOf(k);
const t624 = A.MakeTime(dateOfJd(1949045));
const obs0 = new A.Observer(23, 39, 0);
const stars = [];
for (const line of rows.slice(1)) {
  if (!line) continue;
  const c = line.match(/("[^"]*"|[^,]*)(,|$)/g).map(s => s.replace(/,$/, '').replace(/"/g, ''));
  const mag = +c[ix('mag')];
  if (!(mag <= 4.9) || c[ix('proper')] === 'Sol') continue;
  let ra = +c[ix('ra')] * 15, dec = +c[ix('dec')];
  dec += (+c[ix('pmdec')] || 0) / 3.6e6 * -1376;
  ra += (+c[ix('pmra')] || 0) / 3.6e6 * -1376 / Math.cos(dec * Math.PI / 180);
  A.DefineStar(A.Body.Star1, ((ra / 15) % 24 + 24) % 24, dec, 1000);
  const e = A.Equator(A.Body.Star1, t624, obs0, true, false);
  stars.push([+(e.ra * 15).toFixed(2), +e.dec.toFixed(2), +mag.toFixed(1)]);
}
fs.writeFileSync(path.join(OUT, 'stars.json'), JSON.stringify({ source: 'HYG v4.1 (CC BY-SA 4.0), magnitude 4.9 or brighter, moved to 624 CE', stars }));
console.log('stars', stars.length);
