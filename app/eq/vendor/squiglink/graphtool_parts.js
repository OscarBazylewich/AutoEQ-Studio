// Excerpts from the squiglink / CrinGraph graph tool (0BSD, see LICENSE), as deployed on
// listener800.github.io (assets/js/graphtool.js and config_5128iem.js). Function bodies are
// copied unchanged; only the minimal d3 helpers they call are shimmed below.
// The dB (phon) tables come from both listener800's and squiglink/lab's graphtool.js.
// runAutoEQ() at the end reproduces the AutoEQ button's click handler.

// ---- minimal d3 shims (same semantics as d3 v5 for the calls used here) ----
var d3 = {
    range: function (start, stop, step) {
        if (stop === undefined) { stop = start; start = 0; }
        step = step === undefined ? 1 : step;
        var n = Math.max(0, Math.ceil((stop - start) / step)), r = new Array(n);
        for (var i = 0; i < n; ++i) r[i] = start + i * step;
        return r;
    },
    sum: function (values, valueof) {
        var sum = 0;
        values.forEach(function (v, i) {
            var x = valueof === undefined ? v : valueof(v, i, values);
            if (x = +x) sum += x;
        });
        return sum;
    },
    mean: function (values, valueof) {
        var sum = 0, count = 0;
        values.forEach(function (v, i) {
            var x = valueof === undefined ? v : valueof(v, i, values);
            if (x != null && (x = +x) >= x) { sum += x; ++count; }
        });
        return count ? sum / count : undefined;
    },
    bisect: function (a, x, lo, hi) { // bisectRight
        if (lo == null) lo = 0;
        if (hi == null) hi = a.length;
        while (lo < hi) { var mid = lo + hi >>> 1; if (a[mid] > x) hi = mid; else lo = mid + 1; }
        return lo;
    }
};

// ---- config_5128iem.js ----
function tsvParse(fr) {
    return fr.split(/[\r\n]/)
        .map(l => l.trim()).filter(l => l && l[0] !== '*')
        .map(l => l.split(/[\s,]+/).map(e => parseFloat(e)).slice(0, 2))
        .filter(t => !isNaN(t[0]) && !isNaN(t[1]));
}

// ---- graphtool.js ----
let f_values = (function() {
    // Standard frequencies, all phone need to interpolate to this
    let f = [20];
    let step = Math.pow(2, 1/48); // 1/48 octave
    while (f[f.length-1] < 20000) { f.push(f[f.length-1] * step) }
    return f;
})();
let fr_to_ind = fr => d3.bisect(f_values, fr, 0, f_values.length-1);

function avgCurves(curves) {
    if (!curves.length) return [];
    if (curves.length === 1) return curves[0];
    return curves[0].map((d, i) => {
        let paAvg = d3.mean(curves, c => Math.pow(10, c[i][1] / 20));
        return [d[0], 20 * Math.log10(Math.max(paAvg, Number.EPSILON))];
    });
}

let pair = (arr,fn) => arr.slice(1).map((v,i)=>fn(v,arr[i]));

function smooth_prep(h, d) {
    let rh = h.map(d=>1/d),
        G = [ rh.slice(0,rh.length-1),
              pair(rh, (a,b)=>-(a+b)),
              rh.slice(1) ],
        dv = d3.range(rh.length+1).map(i=>d(i)),
        dG = G.map((r,j) => r.map((e,i) => e*dv[i+j])),
        d2 = dv.map(e=>e*e),
        h6 = h.map(d=>d/6),
        M = [ pair(h6, (a,b)=>2*(a+b)),
              h6.slice(1,h6.length-1),
              h6.slice(3).map(_=>0) ];
    dG.forEach((_,k) =>
        dG.slice(k).forEach((g,i) =>
            dG[i].slice(k).forEach((a,j) => M[k][j] += a*g[j])
        )
    );

    // Diagonal LDL decomposition of M
    let md = [M[0][0]],
        ml = M.slice(1).map(m=>[m[0]/md]);
    d3.range(1,M[0].length).forEach(j => {
        let n = ml.length,
            p = md.slice(-n).reverse().map((d,i)=>d*ml[i][j-1-i]),
            a = M.map((m,k) => m[j] - d3.sum(p.slice(0,n-k),
                      (a,i) => a*ml[k+i][j-1-i]));
        md.push(a[0]);
        ml.forEach((l,j)=>l.push(a[j+1]/a[0]));
    });

    return { G:G, md:md, ml:ml, d2:d2 };
}
function smooth_eval(p, y) {
    let Gy = p.G[0].map(_=>0),
        n = Gy.length;
    p.G.forEach((r,j) => r.forEach((e,i) => Gy[i] += e*y[i+j]));
    // Forward substitution and multiply by p.md
    for (let i=0; i<n; i++) {
        let yi = Gy[i];
        p.ml.forEach((m,k) => { let j=i+k+1; if (j<n) Gy[j] -= m[i]*yi; });
        Gy[i] /= p.md[i];
    }
    // Back substitution
    for (let i=n; i--; ) {
        let yi = Gy[i];
        p.ml.forEach((m,k) => { let j=i-k-1; if (j>=0) Gy[j] -= m[j]*yi; });
    }
    let u = y.slice();
    p.G.forEach((r,j) => r.forEach((e,i) => u[i+j] -= e*p.d2[i+j]*Gy[i]));
    return u;
}

let scale_smoothing = 0.2;   // config_5128iem.js; overwritten by setSiteConfig()
let smooth_level = 3,
    smooth_scale = 0.1*(typeof scale_smoothing !== "undefined" ? scale_smoothing : 1),
    smooth_param = undefined;
function smooth(y, c) {
    if (smooth_level === 0) { return y; }
    let get_param = fv => {
        let x = fv.map(f=>Math.log(f)),
            h = pair(x, (a,b)=>a-b),
            s = smooth_level*smooth_scale,
            d = i => s*Math.pow(1/80,Math.pow(i/x.length,2));
        return smooth_prep(h, d);
    }
    let p;
    if (y.length!==f_values.length) {
        p = get_param(c.map(d=>d[0]));
    } else {
        if (!smooth_param) { smooth_param = get_param(f_values); }
        p = smooth_param;
    }
    return smooth_eval(p, y);
}

// ---- dB (phon) level matching: ISO tables, init_normalize and find_offset from graphtool.js ----
// listener800 (ISO 226:2023 + ISO 389-7:2019)
const ISO2023_params = { // :Updated to comply with both ISO 226:2023 as well as ISO 389-7:2019
    f  : [   20,    25, 31.5,    40,    50,    63,    80,   100,   125,  160,   200,   250,   315,   400,   500,   630,   800, 1000,  1250,  1600,  2000,  2500,  3150,  4000,  5000,  6300,  8000, 10000, 12500],
    a_f: [0.635, 0.602, 0.569, 0.537, 0.509, 0.482, 0.456, 0.433, 0.412, 0.391, 0.373, 0.357, 0.343, 0.33, 0.32, 0.311, 0.303, 0.3, 0.295, 0.292, 0.29, 0.29, 0.289, 0.289, 0.289, 0.293, 0.303, 0.323, 0.354],
    L_U: [-31.5, -27.2,  -23.1, -19.3, -16.1, -13.1, -10.4, -8.2, -6.3, -4.6,  -3.2,    -2.1,  -1.2,  -0.5,     0,   0.4,   0.5,    0,  -2.7,  -4.2,    -1.2,   1.4,   2.3,   1,  -2.3,  -7.2, -11.2, -10.9,  -3.5],
    T_f: [ 78.1,  68.7, 59.5,  51.1,    44,  37.5,  31.5,  26.5,  22.1, 17.9,  14.4,  11.4,   8.4,   5.8,   3.8,     2.1,   1,  0.8,   1.9,   0.5,  -1.5,  -3.1,    -4,  -3.8,  -1.8,     2.5,  6.8,  9.8,  14.4]
};
const ISO2023_free_field = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0.001,0.001,0.002,0.003,0.004,0.006,0.007,0.009,0.011,0.013,0.016,0.018,0.021,0.023,0.026,0.028,0.034,0.042,0.05,0.061,0.072,0.083,0.097,0.109,0.124,0.135,0.155,0.163,0.187,0.2,0.219,0.227,0.237,0.247,0.269,0.272,0.284,0.296,0.308,0.319,0.336,0.348,0.361,0.375,0.388,0.401,0.415,0.428,0.441,0.454,0.468,0.481,0.494,0.506,0.519,0.532,0.544,0.557,0.569,0.581,0.593,0.604,0.616,0.627,0.64,0.652,0.664,0.676,0.684,0.7,0.708,0.723,0.735,0.747,0.759,0.771,0.787,0.799,0.815,0.828,0.845,0.863,0.881,0.895,0.913,0.927,0.945,0.963,0.987,1.01,1.033,1.057,1.075,1.09,1.109,1.127,1.15,1.172,1.194,1.216,1.239,1.261,1.284,1.307,1.331,1.354,1.378,1.402,1.437,1.462,1.502,1.528,1.562,1.597,1.632,1.674,1.71,1.746,1.788,1.825,1.855,1.898,1.935,1.977,2.019,2.05,2.092,2.128,2.176,2.219,2.261,2.308,2.355,2.395,2.435,2.479,2.534,2.587,2.638,2.688,2.727,2.76,2.792,2.826,2.861,2.893,2.924,2.955,2.984,3.013,3.042,3.07,3.098,3.126,3.154,3.182,3.216,3.253,3.292,3.328,3.367,3.412,3.457,3.5,3.544,3.593,3.632,3.691,3.739,3.793,3.848,3.9,3.953,4.011,4.071,4.128,4.202,4.278,4.35,4.435,4.515,4.596,4.684,4.763,4.864,4.933,5.061,5.108,5.262,5.346,5.473,5.527,5.614,5.7,5.904,5.934,6.052,6.172,6.293,6.415,6.602,6.728,6.888,7.051,7.216,7.384,7.554,7.729,7.917,8.11,8.306,8.504,8.705,8.909,9.115,9.322,9.532,9.742,9.954,10.168,10.382,10.597,10.812,11.035,11.34,11.649,11.955,12.257,12.455,12.843,13.032,13.4,13.665,13.92,14.165,14.398,14.691,14.897,15.151,15.317,15.472,15.597,15.703,15.77,15.845,15.891,15.937,15.969,15.989,15.989,15.97,15.933,15.891,15.854,15.795,15.723,15.602,15.466,15.321,15.168,15.009,14.845,14.676,14.504,14.329,14.153,13.976,13.798,13.55,13.375,13.098,12.932,12.756,12.587,12.422,12.236,12.081,11.931,11.761,11.621,11.507,11.353,11.227,11.084,10.949,10.856,10.731,10.629,10.507,10.407,10.312,10.21,10.115,10.036,9.963,9.885,9.795,9.714,9.641,9.577,9.531,9.494,9.461,9.434,9.44,9.456,9.475,9.496,9.517,9.538,9.558,9.575,9.59,9.601,9.608,9.609,9.604,9.589,9.562,9.517,9.408,9.268,9.118,8.971,8.818,8.645,8.509,8.298,8.127,7.938,7.747,7.569,7.391,7.198,7.006,6.832,6.632,6.437,6.257,6.053,5.864,5.678,5.481,5.31,5.095,4.952,4.696,4.604,4.31,4.154,3.925,3.826,3.658,3.49,3.11,3.057,2.848,2.646,2.449,2.259,1.986,1.812,1.604,1.407,1.221,1.046,0.882,0.734,0.634,0.55,0.477,0.412,0.355,0.306,0.262,0.223,0.189,0.159,0.133,0.108,0.086,0.066,0.046].map(v=>v-13);
// squig.link lab (squiglink/lab graphtool.js, ISO 226:2003)
const ISO2003_params = { // :2003
    f  : [   20,    25, 31.5,    40,    50,    63,    80,   100,   125,  160,   200,   250,   315,   400,   500,   630,   800, 1000,  1250,  1600,  2000,  2500,  3150,  4000,  5000,  6300,  8000, 10000, 12500],
    a_f: [0.532, 0.506, 0.48, 0.455, 0.432, 0.409, 0.387, 0.367, 0.349, 0.33, 0.315, 0.301, 0.288, 0.276, 0.267, 0.259, 0.253, 0.25, 0.246, 0.244, 0.243, 0.243, 0.243, 0.242, 0.242, 0.245, 0.254, 0.271, 0.301],
    L_U: [-31.6, -27.2,  -23, -19.1, -15.9,   -13, -10.3,  -8.1,  -6.2, -4.5,  -3.1,    -2,  -1.1,  -0.4,     0,   0.3,   0.5,    0,  -2.7,  -4.1,    -1,   1.7,   2.5,   1.2,  -2.1,  -7.1, -11.2, -10.7,  -3.1],
    T_f: [ 78.5,  68.7, 59.5,  51.1,    44,  37.5,  31.5,  26.5,  22.1, 17.9,  14.4,  11.4,   8.6,   6.2,   4.4,     3,   2.2,  2.4,   3.5,   1.7,  -1.3,  -4.2,    -6,  -5.4,  -1.5,     6,  12.6,  13.9,  12.3]
};
const ISO2003_free_field = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0.0725,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.0896,0,0,0,0,0,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.0967,0,0,0,0,0,0,0,0.0886,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.0656,0,0,0,0,0,0.024,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.045,0,0,0,0,0,0,0.029,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1524,0.2,0.2,0.2386,0.3395,0.4,0.437,0.5,0.5287,0.6225,0.7,0.7063,0.7962,0.8,0.8941,0.9,0.9863,1,1.0729,1.1,1.1544,1.2,1.2504,1.3,1.3,1.3,1.3,1.3163,1.4,1.4,1.4,1.4,1.4017,1.4846,1.5,1.5,1.5748,1.6,1.6,1.653,1.7,1.7,1.7487,1.8,1.8341,1.9,1.9,1.9229,2,2,2,2.1,2.1,2.1897,2.2,2.2,2.2674,2.3,2.3,2.3567,2.4,2.4,2.4446,2.5,2.5262,2.6,2.6234,2.7149,2.8,2.8038,2.9011,2.9969,3.0913,3.1845,3.2762,3.3757,3.4649,3.5617,3.657,3.751,3.8,3.8432,3.9332,4,4,4,4.0121,4.1,4.1,4.1,4.0079,4,4,4,4,3.9334,3.9,3.9,3.9,3.8541,3.8,3.8,3.768,3.7,3.6761,3.6,3.6,3.5927,3.5,3.5,3.5,3.5,3.5,3.5761,3.6,3.6,3.6604,3.7,3.7514,3.8,3.8,3.8349,3.9,3.9218,4.0199,4.1123,4.2076,4.3016,4.3985,4.6816,5.0515,5.4222,5.8036,6.1097,6.4656,6.8461,7.3316,7.9083,8.4305,8.9369,9.5105,10.0759,10.6024,11.0027,11.4847,12.0482,12.5152,12.8994,13.2776,13.7381,14.1303,14.5168,14.8858,15.273,15.6547,15.9731,16.2596,16.542,16.7857,17.0111,17.2325,17.3532,17.522,17.6,17.6,17.6,17.6,17.5044,17.41,17.3145,17.2205,17.1255,17.0318,16.9373,16.784,16.6459,16.4536,16.2578,16.1234,15.967,15.8736,15.7552,15.566,15.3879,15.2881,15.0958,14.9064,14.8099,14.6287,14.5201,14.3477,14.2307,14.0709,13.9399,13.7916,13.6514,13.5552,13.4604,13.367,13.2718,13.1766,13.0812,12.9743,12.7916,12.6975,12.602,12.5078,12.3247,12.0547,11.7686,11.4154,11.1009,10.9385,10.7344,10.3998,10.0163,9.6382,9.2957,8.9799,8.6248,8.3404,8.0424,7.674,7.3851,7.0061,6.5307,6.1484,5.7696,5.4662,5.1084,4.7302,4.3498,3.971,3.6455,3.4075,3.1343,2.7917,2.5376,2.3484,2.1585,1.9849,1.9107,2,2,2,2.0894,2.1844,2.2787,2.374,2.6057,2.8265,3.0161,3.2057,3.3954,3.5851,3.8122,4.0967,4.354,4.5651,4.8509,5.1459,5.5259,5.9041,6.1881,6.5643,6.8561,7.1418,7.4251,7.7093,8.0593,8.3192,8.4541,8.5493,8.6437,8.7,8.7336,8.8,8.8,8.8,8.8,8.7926,8.7,8.7,8.6079,8.5133,8.5,8.4237,8.1863,7.968,7.7786,7.4219,6.948,6.4299,5.8212,5.1563,4.4634,3.7042,2.8897,1.9005,1.2368,0.5651,-0.2856,-0.8593,-2.9].map(v=>v-7);
let iso223_params = ISO2023_params, free_field = ISO2023_free_field;  // chosen by setSiteConfig()

function init_normalize(fv) { // Interpolate values for find_offset
    let par = [], ff = [];
    par.free_field = ff;
    const p = iso223_params;
    let i = 0;
    fv.forEach(function (f) {
        if (f >= p.f[i]) { i++; }
        let i0 = Math.max(0,i-1),
            i1 = Math.min(i,p.f.length-1),
            g;
        if (i0===i1) {
            g = n => p[n][i0];
        } else {
            let ll= [p.f[i0],p.f[i1],f].map(x=>Math.log(x)),
                l = (ll[2]-ll[0])/(ll[1]-ll[0]);
            g = n => { let v=p[n]; return v[i0]+l*(v[i1]-v[i0]); };
        }
        let a = g("a_f"),
            m = a * (Math.log10(4)-10 + g("L_U")/10),
            k = (0.005076/Math.pow(10,m)) - Math.pow(10, a*g("T_f")/10),
            c = Math.pow(10, 9.4 + 4*m) / fv.length;
        par.push({a:a, k:k, c:c});
        let ffi = Math.floor(0.5+48*Math.log2(f/19.4806));
        ff.push(free_field[Math.max(0,Math.min(479,ffi))]);
    });
    return par;
}

// Find the appropriate offset (in dB) for fr so that the total loudness
// is equal to target (in phon)
let norm_par = []; // Cached interpolated ISO parameters
function find_offset(c, target) {
    let par;
    if (c.length!==f_values.length) {
        par = init_normalize(c.map(d=>d[0]));
    } else {
        if (!norm_par.length) { norm_par = init_normalize(f_values); }
        par = norm_par;
    }
    let fr = c.map(v=>v[1]);
    let x = 0; // Initial offset
    function getStep(o) {
        const l10 = Math.log(10)/10;
        let v=0, d=0;
        par.forEach(function (p,i) {
            let a=p.a, k=p.k, c=p.c, ds,v0,v1;
            v0  = Math.exp(l10*(fr[i]+o-par.free_field[i]));
            ds  = l10 * v0;
            v1  = k + Math.pow(v0,a);
            ds *= a * Math.pow(v0,a-1);
            v  += c * Math.pow(v1,4);
            ds *= c * 4 * Math.pow(v1,3);
            d  += ds;
        });
        // value: Math.log(v)/l10
        // deriv: d / (l10*v)
        return (Math.log(v) - target*l10) * (v/d);
    }
    let dx;
    do {
        dx = getStep(x);
        x -= dx;
    } while (Math.abs(dx) > 0.01);
    return x;
}

// normalizePhone(): "Hz~"/"Hz" use the display-smoothed channels; "dB" (phon) uses getAvg() of them
let norm_sel = 1, norm_fr = 500, norm_fr_range = true, norm_phon = 60;
function normOf(channels) {
    if (!norm_sel) { // phon
        return find_offset(channels.length === 1 ? channels[0] : avgCurves(channels), norm_phon);
    }
    let avg = l => 20 * Math.log10(Math.max(d3.mean(l, d => Math.pow(10, d / 20)), Number.EPSILON));
    if (norm_fr_range) {
        // 4-octave window (±2 octaves): average all channels over the range
        let iLow  = fr_to_ind(norm_fr / 4);
        let iHigh = fr_to_ind(norm_fr * 4);
        let vals = [].concat(...channels.map(ch => ch.slice(iLow, iHigh + 1).map(d => d[1])));
        return 60 - avg(vals);
    } else {
        let i = fr_to_ind(norm_fr);
        return 60 - avg(channels.map(l=>l[i][1]));
    }
}

// ---------------------------------------------------------------------------
// Glue used by the Python front end
// ---------------------------------------------------------------------------
let STATE = null;

function setSiteConfig(cfg) {
    scale_smoothing = cfg.scale_smoothing;
    smooth_level = cfg.smooth_level;
    smooth_scale = 0.1 * scale_smoothing;
    smooth_param = undefined;
    norm_sel = cfg.normalization === "dB" ? 0 : 1;
    norm_fr = cfg.norm_hz;
    norm_fr_range = cfg.normalization === "Hz~";
    norm_phon = cfg.norm_db;
    let iso = cfg.phon_table === "ISO 226:2003";
    iso223_params = iso ? ISO2003_params : ISO2023_params;
    free_field = iso ? ISO2003_free_field : ISO2023_free_field;
    norm_par = [];
    Equalizer.config.TrebleStartFrom = cfg.treble_start_from;
    Equalizer.config.DefaultSampleRate = cfg.sample_rate || 48000;
}

// listener800 "Custom DF" target adjustments (updateDF in graphtool.js): five filters, then tilt in dB/oct.
function adjustTarget(ch, a) {
    if (!a) return ch;
    let filters = [
        {disabled: false, type:"LSQ", freq:a.bass_freq, q:a.bass_q, gain:a.bass_gain},
        {disabled: false, type:"PK", freq:a.ear_freq, q:a.ear_q, gain:a.ear_gain},
        {disabled: false, type:"HSQ", freq:a.treble_freq, q:a.treble_q, gain:a.treble_gain},
        {disabled: false, type:"HSQ", freq:a.halftilt_freq, q:0.4, gain:a.halftilt_gain},
        {disabled: false, type:"HSQ", freq:a.air_freq, q:a.air_q, gain:a.air_gain}
    ];
    let bass = Equalizer.apply(ch, filters);
    return bass.map(([f, v]) => [f, v + a.tilt * Math.log2(f)]);
}

// Load files exactly like loadFiles()/Upload Target, then smooth + normalise like showPhone().
function loadCurves(measTexts, targetText, adjust) {
    let raw = measTexts.map(t => Equalizer.interp(f_values, tsvParse(t)));
    let tRaw = [adjustTarget(Equalizer.interp(f_values, tsvParse(targetText)), adjust)];
    let smoothCh = chs => chs.map(c => smooth(c.map(d=>d[1]), c).map((d,i)=>[c[i][0],d]));
    let pNorm = normOf(smoothCh(raw)), tNorm = normOf(smoothCh(tRaw));
    // AutoEQ button handler
    let phoneCHs = raw.map(ch => ch.map(([f, v]) => [f, v + pNorm]));
    let phoneCH = (phoneCHs.length > 1) ? avgCurves(phoneCHs) : phoneCHs[0];
    let targetCH = tRaw[0].map(([f, v]) => [f, v + tNorm]);
    STATE = { raw, phoneCH, targetCH, pNorm, tNorm };
    return { f: f_values, meas: phoneCH.map(d=>d[1]), target: targetCH.map(d=>d[1]), pNorm, tNorm, nch: raw.length,
             channels: raw.map(c => c.map(d => d[1] + pNorm)) };
}

// Search preview: level one device like showPhone() and average its files like the average line.
function previewCurve(texts) {
    let raw = texts.map(t => Equalizer.interp(f_values, tsvParse(t)));
    let sm = raw.map(c => smooth(c.map(d=>d[1]), c).map((d,i)=>[c[i][0],d]));
    let n = normOf(sm);
    let chs = raw.map(ch => ch.map(([f, v]) => [f, v + n]));
    return (chs.length > 1 ? avgCurves(chs) : chs[0]).map(d => d[1]);
}

// Number of usable points in a file (the site rejects uploads with fewer than 32)
// (different frequencies above 0 Hz: a file repeating one line isn't a frequency response)
function countPoints(text) { return new Set(tsvParse(text).filter(t => t[0] > 0).map(t => t[0])).size; }

// "Export Graphic EQ" (Wavelet) text, as the site builds it
function graphicEQText(filters) {
    let graphicEQ = Equalizer.as_graphic_eq(filters);
    return "GraphicEQ: " + graphicEQ.map(([f, gain]) => f.toFixed(0) + " " + gain.toFixed(1)).join("; ");
}

// One AutoEQ click with the panel's field parsing/clamping.
function runAutoEQ(rows, lo, hi, gmin, gmax, qmin, qmax) {
    let autoEQFrom = Math.min(Math.max(parseInt(String(lo)) || 0, 20), 20000);
    let autoEQTo = Math.min(Math.max(parseInt(String(hi)) || 0, autoEQFrom), 20000);
    Equalizer.config.AutoEQRange = [autoEQFrom, autoEQTo];
    let autoEQGainFrom = Math.min(Math.max(parseInt(String(gmin)) || 0, -20), 20);
    let autoEQGainTo = Math.min(Math.max(parseInt(String(gmax)) || 0, autoEQGainFrom), 20);
    Equalizer.config.OptimizeGainRange = [autoEQGainFrom, autoEQGainTo];
    let autoEQQFrom = Math.min(Math.max(parseFloat(String(qmin)) || 0, 0.1), 5);
    let autoEQQTo = Math.min(Math.max(parseFloat(String(qmax)) || 0, autoEQQFrom), 5);
    Equalizer.config.OptimizeQRange = [autoEQQFrom, autoEQQTo];
    let filters = Equalizer.autoeq(STATE.phoneCH, STATE.targetCH, rows);
    // updatePreampDisplay(): first channel before/after EQ
    let preamp = Equalizer.calc_preamp(STATE.raw[0], Equalizer.apply(STATE.raw[0], filters));
    let eq = Equalizer.apply(STATE.phoneCH, filters).map(d=>d[1]);
    return { filters, preamp, eq, effective: [autoEQFrom, autoEQTo, autoEQGainFrom, autoEQGainTo, autoEQQFrom, autoEQQTo] };
}
