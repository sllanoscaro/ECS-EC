/**007 finite query admission. Only this trusted router chooses upstreams/paths.
 * Inputs are untrusted HTTP; outputs finite read responses or fixed denial codes.
 * No URL, body, subject, credential, exception or backend diagnostic is logged.
 */

/** Return an encoded argument string after rejecting duplicate or oversized values. */
function argumentsFor(r) {
    const result = {};
    const keys = Object.keys(r.args);
    for (let i = 0; i < keys.length; i++) {
        const key = keys[i];
        const value = r.args[key];
        if (typeof value !== 'string' || value.length > 65536 || !/^[a-zA-Z_][a-zA-Z_0-9.]*$/.test(key)) throw Error();
        result[key] = value;
    }
    return result;
}

/** Admit finite source limits; unknown parameters fail closed instead of becoming proxy controls. */
function boundedArgs(args, allowed) {
    Object.keys(args).forEach(key => { if (!allowed.includes(key)) throw Error(); });
    if (args.limit !== undefined && !/^(?:[1-9][0-9]{0,3}|10000)$/.test(args.limit)) throw Error();
    args.limit = args.limit || '1000';
    return args;
}

/** Encode only validated argument names; never interpolate user input into a proxy URL. */
function encode(args) {
    return Object.keys(args).map(k => encodeURIComponent(k) + '=' + encodeURIComponent(args[k])).join('&');
}

/** Convert explicit source instants to milliseconds for bounding; preserve original nanosecond strings. */
function instant(value) {
    if (/^[0-9]+(?:\.[0-9]+)?$/.test(value)) {
        const number = Number(value);
        return number > 1e16 ? number / 1e6 : number > 1e11 ? number : number * 1000;
    }
    return Date.parse(value);
}

/** Ensure queries never span more than24h; omitted source bounds use a15min default. */
function timeRange(args) {
    const now = Date.now();
    if (args.start === undefined) args.start = String((now - 900000) / 1000);
    if (args.end === undefined) args.end = String(now / 1000);
    const start = instant(args.start), end = instant(args.end);
    if (!Number.isFinite(start) || !Number.isFinite(end) || end < start || end - start > 86400000) throw Error();
    return args;
}

/** Authorize only provisioned datasource query models, finite windows, body and result limits. */
function queryBody(r) {
    const raw = r.requestText || '';
    if (Buffer.byteLength(raw) > 65536) throw Error();
    const body = JSON.parse(raw);
    if (!body || !Array.isArray(body.queries) || body.queries.length < 1 || body.queries.length > 4) throw Error();
    if (!/^[0-9]{13}$/.test(String(body.from)) || !/^[0-9]{13}$/.test(String(body.to))) throw Error();
    if (Number(body.to) <= Number(body.from) || Number(body.to) - Number(body.from) > 86400000) throw Error();
    for (let i = 0; i < body.queries.length; i++) {
        const q = body.queries[i];
        if (!q || !q.datasource || q.datasource.uid !== 'ecs-loki' || q.datasource.type !== 'loki') throw Error();
        if (q.maxLines !== undefined && (!Number.isInteger(q.maxLines) || q.maxLines < 1 || q.maxLines > 10000)) throw Error();
        q.maxLines = q.maxLines || 1000;
        if (q.maxDataPoints !== undefined && (!Number.isInteger(q.maxDataPoints) || q.maxDataPoints < 1 || q.maxDataPoints > 10000)) throw Error();
        q.maxDataPoints = q.maxDataPoints || 1000;
    }
    return JSON.stringify(body);
}

/** Route human reads after Basic authorization; default denial is independent of upstream health. */
async function read(r) {
    let target, args, body = '';
    try {
        const path = r.uri;
        // Inspect original encoding as well as normalized URI; normalization must never
        // turn a forbidden traversal/double slash into an allowed route.
        const original = r.variables.request_uri.split('?')[0];
        if (original.includes('%') || original.includes('//') || original.includes('/./') || original.includes('/../') || original.includes('\\')) throw Error();
        args = argumentsFor(r);
        const method = r.method;
        if (path === '/grafana/api/ds/query' && method === 'POST') {
            Object.keys(args).forEach(key => { if (key !== 'ds_type' && key !== 'requestId') throw Error(); });
            body = queryBody(r);
            target = '/_grafana/api/ds/query';
        } else {
            if (method !== 'GET' && method !== 'HEAD') { r.return(405); return; }
            if (/^\/logs\/loki\/api\/v1\/(query|query_range)$/.test(path)) {
                boundedArgs(args, ['query', 'start', 'end', 'time', 'step', 'interval', 'direction', 'limit']);
                timeRange(args);
                target = '/_loki' + path.slice('/logs'.length);
            } else if (path === '/logs/loki/api/v1/labels' || /^\/logs\/loki\/api\/v1\/label\/(service_name|environment|operation|outcome|severity)\/values$/.test(path)) {
                Object.keys(args).forEach(key => { if (!['start', 'end', 'query'].includes(key)) throw Error(); });
                timeRange(args);
                target = '/_loki' + path.slice('/logs'.length);
            } else if (/^\/jaeger\/api\/(?:v3\/)?(?:services|operations|traces)$/.test(path) || /^\/jaeger\/api\/(?:v3\/)?traces\/[0-9a-f]{32}$/.test(path) || path === '/jaeger/api/services/ecs-ec/operations') {
                if (path === '/jaeger/api/v3/traces') {
                    const allowed = ['query.serviceName', 'query.operationName', 'query.startTimeMin', 'query.startTimeMax',
                        'query.durationMin', 'query.durationMax', 'query.searchDepth', 'query.rawTraces',
                        'query.filter'];
                    Object.keys(args).forEach(k => { if (!allowed.includes(k)) throw Error(); });
                    if (args['query.searchDepth'] !== undefined && !/^(?:[1-9][0-9]{0,3}|10000)$/.test(args['query.searchDepth'])) throw Error();
                    args['query.searchDepth'] = args['query.searchDepth'] || '1000';
                    args['query.startTimeMin'] = args['query.startTimeMin'] || new Date(Date.now() - 900000).toISOString();
                    args['query.startTimeMax'] = args['query.startTimeMax'] || new Date().toISOString();
                    const start = Date.parse(args['query.startTimeMin']), end = Date.parse(args['query.startTimeMax']);
                    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start || end - start > 86400000) throw Error();
                } else if (/^\/jaeger\/api\/v3\/traces\//.test(path)) {
                    Object.keys(args).forEach(k => { if (!['startTime', 'endTime', 'rawTraces'].includes(k)) throw Error(); });
                    if (args.startTime || args.endTime) {
                        const start = Date.parse(args.startTime), end = Date.parse(args.endTime);
                        if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start || end - start > 86400000) throw Error();
                    }
                } else if (path === '/jaeger/api/traces') {
                    boundedArgs(args, ['service', 'operation', 'start', 'end', 'limit', 'lookback', 'tags', 'minDuration', 'maxDuration']);
                    args.start = args.start || String((Date.now() - 900000) * 1000);
                    args.end = args.end || String(Date.now() * 1000);
                    const start = Number(args.start), end = Number(args.end);
                    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start || end - start > 86400e6) throw Error();
                } else {
                    Object.keys(args).forEach(k => { if (!['service', 'spanKind'].includes(k)) throw Error(); });
                }
                target = '/_jaeger' + path;
            } else if (path === '/jaeger/' || path === '/jaeger/search' || /^\/jaeger\/trace\/[0-9a-f]{32}$/.test(path) || /^\/jaeger\/static\/[a-zA-Z0-9_./-]+\.(?:js|css|png|svg|woff2?|ico|map)$/.test(path)) {
                target = '/_jaeger' + path;
            } else if (/^\/grafana\/apis\/dashboard\.grafana\.app\/$/.test(path) ||
                /^\/grafana\/apis\/dashboard\.grafana\.app\/(?:v0alpha1|v1beta1|v2beta1|v1|v2)\/namespaces\/default\/dashboards\/ecs-platform(?:\/dto)?$/.test(path) ||
                /^\/grafana\/apis\/preferences\.grafana\.app\/v1\/namespaces\/default\/preferences(?:\/merged)?$/.test(path) ||
                path === '/grafana/apis/collections.grafana.app/v1alpha1/namespaces/default/stars') {
                target = '/_grafana' + path.slice('/grafana'.length);
            } else if (path === '/grafana/' || /^\/grafana\/d\/ecs-platform\/[a-zA-Z0-9-]+$/.test(path) ||
                /^\/grafana\/public\/[a-zA-Z0-9_./@-]+\.(?:js|css|png|svg|woff2?|ico|json|map)$/.test(path) ||
                /^\/grafana\/api\/(?:frontend\/settings|user|user\/preferences|user\/orgs|login\/ping|org|search|folders|dashboards\/home|dashboards\/uid\/ecs-platform|datasources|datasources\/uid\/ecs-loki)$/.test(path)) {
                target = '/_grafana' + path.slice('/grafana'.length);
            } else { r.return(403); return; }
        }
        // A timer bounds the whole subrequest, independently of upstream idle timeouts.
        let timer;
        const timeout = new Promise(resolve => { timer = setTimeout(() => resolve(null), 30000); });
        const response = await Promise.race([r.subrequest(target, {args: encode(args), method: method, body: body}), timeout]);
        clearTimeout(timer);
        if (!response) { r.return(504); return; }
        r.headersOut['Content-Type'] = response.headersOut['Content-Type'] || 'application/octet-stream';
        r.headersOut['Cache-Control'] = 'no-store';
        // No cookie/session/Location or untrusted identity header can cross this boundary.
        r.return(response.status, response.responseBuffer);
    } catch (_) { r.return(400); }
}

/** Authorize exactly one process certificate for its exact mTLS endpoint/method. */
async function ingest(r) {
    const env = process.env.OBS_ENVIRONMENT || 'local';
    const identities = {'8444': ['app', '/v1/traces', 'POST', '/_otlp/v1/traces'],
                        '8445': ['alloy', '/loki/api/v1/push', 'POST', '/_loki/loki/api/v1/push'],
                        '8446': ['health', '/collector-health', 'GET', '/_alloy/metrics']};
    const rule = identities[r.variables.server_port];
    if (!rule || r.variables.ssl_client_verify !== 'SUCCESS' ||
        r.variables.ssl_client_s_dn !== 'CN=ecs-obs-' + env + '-' + rule[0] ||
        r.uri !== rule[1] || r.method !== rule[2] || r.variables.args) { r.return(403); return; }
    try {
        const response = await r.subrequest(rule[3], {method: r.method, body: r.requestBuffer || ''});
        if (rule[0] === 'health') {
            // Only permitted transport counters cross the health boundary, never all
            // tool metrics/labels. Drop all labels before the monolith receives them.
            const values = {'loki_write_sent_entries_total': 0, 'loki_write_dropped_entries_total': 0};
            const found = {};
            const linesIn = response.responseText.split('\n');
            for (let i = 0; i < linesIn.length; i++) {
                const line = linesIn[i];
                const match = /^(loki_write_sent_entries_total|loki_write_dropped_entries_total)(?:\{[^\n]*\})?\s+([0-9.e+]+)$/.exec(line);
                if (match) { values[match[1]] += Number(match[2]); found[match[1]] = true; }
            }
            const lines = Object.keys(found).map(k => k + ' ' + values[k]).join('\n');
            r.return(response.status, lines + '\n');
        } else r.return(response.status, '');
    } catch (_) { r.return(502); }
}

export default {read, ingest};
