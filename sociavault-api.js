/**
 * sociavault-api.js
 * SociaVault API client for PollNex Insights
 *
 * Integrates with the SociaVault social-data platform to fetch trending topics,
 * sentiment scores, and engagement metrics relevant to the Haitian market and
 * its diaspora.  Replace BASE_URL and set your API key before going to
 * production.
 *
 * Usage:
 *   import SociaVaultClient from './sociavault-api.js';
 *   const sv = new SociaVaultClient({ apiKey: 'YOUR_KEY' });
 *   const trends = await sv.getTrendingTopics({ region: 'HT', limit: 5 });
 */

const SOCIAVAULT_BASE_URL = 'https://api.sociavault.com/v1';

/**
 * Lightweight HTTP helper — wraps fetch with JSON handling and error
 * normalisation.
 */
async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const body = await response.text().catch(() => '');
    throw new Error(
      `SociaVault API error ${response.status}: ${response.statusText}. ${body}`
    );
  }

  return response.json();
}

/**
 * SociaVaultClient
 *
 * All public methods return Promises that resolve with the parsed JSON payload
 * from SociaVault, or reject with a descriptive Error.
 */
export default class SociaVaultClient {
  /**
   * @param {object} config
   * @param {string} config.apiKey   - Your SociaVault API key.
   * @param {string} [config.baseUrl] - Override the default API base URL.
   * @param {number} [config.timeoutMs=8000] - Request timeout in milliseconds.
   */
  constructor({ apiKey, baseUrl = SOCIAVAULT_BASE_URL, timeoutMs = 8000 } = {}) {
    if (!apiKey) throw new Error('SociaVaultClient: apiKey is required.');
    this._apiKey = apiKey;
    this._base = baseUrl.replace(/\/$/, '');
    this._timeoutMs = timeoutMs;
  }

  /** Build an authenticated fetch call, honouring the configured timeout. */
  _fetch(path, options = {}) {
    const url = `${this._base}${path}`;
    const controller = new AbortController();
    const tid = setTimeout(() => controller.abort(), this._timeoutMs);

    return apiFetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        Authorization: 'Bearer ' + this._apiKey,
        ...(options.headers || {}),
      },
    }).finally(() => clearTimeout(tid));
  }

  // ─────────────────────────────────────────────────────────────────────────
  // WORKFLOW METHODS
  // ─────────────────────────────────────────────────────────────────────────

  /**
   * Fetch trending topics for a given region / keyword set.
   *
   * @param {object}  [params]
   * @param {string}  [params.region='HT']     ISO-3166-1 alpha-2 country code.
   * @param {string}  [params.language='fr']   BCP-47 language tag.
   * @param {number}  [params.limit=10]        Maximum topics to return.
   * @param {string}  [params.category]        Optional category filter (e.g.
   *                                           'commerce', 'politics', 'health').
   * @returns {Promise<{topics: Array<{name:string, volume:number, delta:number}>}>}
   */
  getTrendingTopics({ region = 'HT', language = 'fr', limit = 10, category } = {}) {
    const qs = new URLSearchParams({ region, language, limit: String(limit) });
    if (category) qs.set('category', category);
    return this._fetch(`/trends/topics?${qs}`);
  }

  /**
   * Fetch aggregated sentiment scores for one or more keywords.
   *
   * @param {object}         params
   * @param {string[]}       params.keywords  Terms to analyse.
   * @param {string}         [params.region='HT']
   * @param {string}         [params.since]   ISO-8601 start date (YYYY-MM-DD).
   * @param {string}         [params.until]   ISO-8601 end date  (YYYY-MM-DD).
   * @returns {Promise<{results: Array<{keyword:string, positive:number,
   *           neutral:number, negative:number, sampleSize:number}>}>}
   */
  getSentimentAnalysis({ keywords, region = 'HT', since, until } = {}) {
    if (!keywords || keywords.length === 0) {
      return Promise.reject(new Error('getSentimentAnalysis: at least one keyword is required.'));
    }
    const body = { keywords, region, ...(since && { since }), ...(until && { until }) };
    return this._fetch('/sentiment/aggregate', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  /**
   * Fetch cross-platform engagement metrics for a brand / handle.
   *
   * @param {object}  params
   * @param {string}  params.handle       Social handle or brand slug.
   * @param {string}  [params.platform]   Filter to a single platform
   *                                      ('twitter'|'facebook'|'instagram'|'tiktok').
   * @param {string}  [params.since]      ISO-8601 start date (YYYY-MM-DD).
   * @param {string}  [params.until]      ISO-8601 end date  (YYYY-MM-DD).
   * @returns {Promise<{handle:string, platforms:Array<{name:string,
   *           followers:number, impressions:number, engagementRate:number}>}>}
   */
  getEngagementMetrics({ handle, platform, since, until } = {}) {
    if (!handle) return Promise.reject(new Error('getEngagementMetrics: handle is required.'));
    const qs = new URLSearchParams({ handle });
    if (platform) qs.set('platform', platform);
    if (since)    qs.set('since', since);
    if (until)    qs.set('until', until);
    return this._fetch(`/engagement/metrics?${qs}`);
  }

  /**
   * Run the full PollNex social-intelligence workflow:
   *   1. Fetch trending topics for the Haitian market.
   *   2. Derive sentiment scores for the top topics.
   *   3. Return a unified report object.
   *
   * @param {object} [options]
   * @param {string} [options.region='HT']
   * @param {string} [options.language='fr']
   * @param {number} [options.topN=5]  Number of trending topics to analyse.
   * @returns {Promise<WorkflowReport>}
   */
  async runSocialInsightsWorkflow({ region = 'HT', language = 'fr', topN = 5 } = {}) {
    // Step 1 — trending topics
    const { topics } = await this.getTrendingTopics({ region, language, limit: topN });

    // Step 2 — sentiment for each trending keyword (parallel)
    const keywords = topics.map(t => t.name);
    const { results: sentimentResults } = await this.getSentimentAnalysis({ keywords, region });

    // Step 3 — merge into a unified report
    const sentimentMap = Object.fromEntries(
      sentimentResults.map(r => [r.keyword, r])
    );

    return {
      generatedAt: new Date().toISOString(),
      region,
      language,
      insights: topics.map(topic => ({
        topic: topic.name,
        volume: topic.volume,
        volumeDelta: topic.delta,
        sentiment: sentimentMap[topic.name] ?? null,
      })),
    };
  }
}

/**
 * @typedef {object} WorkflowReport
 * @property {string}         generatedAt  ISO-8601 timestamp.
 * @property {string}         region       ISO-3166-1 alpha-2 code.
 * @property {string}         language     BCP-47 language tag.
 * @property {InsightEntry[]} insights     One entry per trending topic.
 */

/**
 * @typedef {object} InsightEntry
 * @property {string}  topic        Trending topic name.
 * @property {number}  volume       Mention count.
 * @property {number}  volumeDelta  % change vs. previous period.
 * @property {object|null} sentiment Sentiment scores (positive/neutral/negative)
 *                                   or null when unavailable.
 */
