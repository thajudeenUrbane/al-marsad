#!/usr/bin/env node
/*
 * Lab: Badr. The sky over Badr on the eve of 17 Ramadan 2 AH, under two calendar assumptions.
 *
 *   node lab/badr/sky.cjs <hyg.csv> <astronomy-engine dir>   # writes lab/badr/data/sky.json
 *
 * COMPUTED, not attested: astronomy-engine (MIT) for the Sun and Moon, the HYG star catalogue
 * (CC BY-SA 4.0) moved back to 624 CE by proper motion and precessed to that date. The source
 * gives a weekday and a lunar date, never a Julian date; which lunation was Ramadan in 2 AH is a
 * question for the scholars (intercalation before 10 AH), so the page draws one sky per assumption.
 */
const fs = require('fs');
const path = require('path');
const [csvPath, aeDir] = process.argv.slice(2);
const A = require(path.resolve(aeDir));

const BADR = { lat: 23.72676, lon: 38.80098, h: 40, src: 'al-Thurayya BADR_388E237N_S (CC BY 4.0), proposed' };
const obs = new A.Observer(BADR.lat, BADR.lon, BADR.h);
const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

function jdJulian(y, m, d) { if (m <= 2) { y--; m += 12; } return Math.floor(365.25 * (y + 4716)) + Math.floor(30.6001 * (m + 1)) + d - 1524.5; }
function dateOfJd(jd) { return new Date((jd - 2440587.5) * 86400000); }
function julianOf(t) {
  const jd = t.ut + 2451545.0, Z = Math.floor(jd + 0.5), F = jd + 0.5 - Z;
  const B = Z + 1524, C = Math.floor((B - 122.1) / 365.25), D = Math.floor(365.25 * C), E = Math.floor((B - D) / 30.6001);
  const day = Math.floor(B - D - Math.floor(30.6001 * E) + F), mon = E < 14 ? E - 1 : E - 13, yr = mon > 2 ? C - 4716 : C - 4715;
  return { y: yr, m: mon, d: day, weekday: DAYS[(Math.floor(jd + 0.5) + 1) % 7] };
}
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const fmt = j => `${j.weekday} ${j.d} ${MONTHS[j.m - 1]} ${j.y}`;

// A lunation's month begins the evening the crescent is first seen; take the first evening the
// Moon is at least 30 hours past conjunction and 8 degrees up at sunset (a stated, simple rule).
function scenario(key, conjSearchFrom) {
  const conj = A.SearchMoonPhase(0, A.MakeTime(dateOfJd(conjSearchFrom)), 40);
  let ss = A.SearchRiseSet(A.Body.Sun, obs, -1, conj, 3);
  while (true) {
    const age = (ss.ut - conj.ut) * 24;
    const hor = A.Horizon(ss, obs, ...(() => { const e = A.Equator(A.Body.Moon, ss, obs, true, true); return [e.ra, e.dec]; })(), 'normal');
    if (age >= 30 && hor.altitude >= 8) break;
    ss = A.SearchRiseSet(A.Body.Sun, obs, -1, ss.AddDays(0.5), 3);
  }
  const crescentEve = ss;
  const eve17 = A.SearchRiseSet(A.Body.Sun, obs, -1, crescentEve.AddDays(15.5), 3);   // the evening that begins the 17th
  const morning17 = A.SearchRiseSet(A.Body.Sun, obs, +1, eve17, 1);
  const frames = [];
  for (let t = eve17.AddDays(-0.5 / 24); t.ut <= morning17.ut + 0.5 / 24; t = t.AddDays(15 / 1440)) {
    const m = A.Equator(A.Body.Moon, t, obs, true, true), mh = A.Horizon(t, obs, m.ra, m.dec, 'normal');
    const s = A.Equator(A.Body.Sun, t, obs, true, true), sh = A.Horizon(t, obs, s.ra, s.dec, 'normal');
    frames.push({ ut: t.date.toISOString().slice(11, 16), lst: +(A.SiderealTime(t) * 15 + BADR.lon).toFixed(3),
      moon: [+mh.altitude.toFixed(2), +mh.azimuth.toFixed(2)], sun: [+sh.altitude.toFixed(2), +sh.azimuth.toFixed(2)] });
  }
  const ill = A.Illumination(A.Body.Moon, eve17);
  const mr = A.SearchRiseSet(A.Body.Moon, obs, +1, eve17, 1);
  return {
    key,
    conjunction: fmt(julianOf(conj)),
    crescent_evening: fmt(julianOf(crescentEve)),
    eve_of_17: fmt(julianOf(eve17)),
    morning_of_17: fmt(julianOf(morning17)),
    moon_illuminated_pct: +(ill.phase_fraction * 100).toFixed(1),
    moonrise_minutes_after_sunset: Math.round((mr.ut - eve17.ut) * 1440),
    local_offset_minutes: Math.round(BADR.lon * 4),
    frames,
  };
}

// Stars: apparent place of date, 624 CE (proper motion from J2000, then precession and nutation).
function stars(t) {
  const rows = fs.readFileSync(csvPath, 'utf8').split('\n');
  const head = rows[0].split(',').map(s => s.replace(/"/g, ''));
  const ix = k => head.indexOf(k);
  const years = -1376;
  const out = [];
  for (const line of rows.slice(1)) {
    if (!line) continue;
    const c = line.match(/("[^"]*"|[^,]*)(,|$)/g).map(s => s.replace(/,$/, '').replace(/"/g, ''));
    const mag = +c[ix('mag')];
    if (!(mag <= 4.9) || c[ix('proper')] === 'Sol') continue;
    let ra = +c[ix('ra')] * 15, dec = +c[ix('dec')];
    const pmra = +c[ix('pmra')] || 0, pmdec = +c[ix('pmdec')] || 0;
    dec += pmdec / 3.6e6 * years;
    ra += pmra / 3.6e6 * years / Math.cos(dec * Math.PI / 180);
    A.DefineStar(A.Body.Star1, ((ra / 15) % 24 + 24) % 24, dec, 1000);
    const e = A.Equator(A.Body.Star1, t, obs, true, false);
    const name = c[ix('proper')] || '';
    out.push([+(e.ra * 15).toFixed(2), +e.dec.toFixed(2), +mag.toFixed(1), name]);
  }
  return out;
}

const a = scenario('feb', jdJulian(624, 2, 15));
const b = scenario('mar', jdJulian(624, 3, 15));
const data = {
  place: BADR,
  method: 'astronomy-engine 2.1.19 (MIT); HYG v4.1 (CC BY-SA 4.0), stars to magnitude 4.9, proper motion back 1,376 years, precessed to date',
  crescent_rule: 'Month begins the first evening the Moon is 30 hours past conjunction and 8 degrees above the horizon at sunset (a simple stand-in for crescent sighting).',
  scenarios: [a, b],
  stars: stars(A.MakeTime(dateOfJd(jdJulian(624, 3, 12)))),
};
fs.mkdirSync(path.join(__dirname, 'data'), { recursive: true });
fs.writeFileSync(path.join(__dirname, 'data', 'sky.json'), JSON.stringify(data));
for (const s of [a, b]) console.log(s.key, s.conjunction, '| crescent', s.crescent_evening, '| eve of 17th', s.eve_of_17, '| morning', s.morning_of_17, '|', s.moon_illuminated_pct + '%', s.moonrise_minutes_after_sunset + ' min');
console.log('stars', data.stars.length, 'bytes', JSON.stringify(data).length);
