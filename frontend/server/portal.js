import { readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';

export const DEFAULT_PORTAL = {
  url: 'https://transparencia.marica.rj.gov.br/e-cidade/contratos/padrao',
  name: 'Maricá - RJ',
  isECidade: true,
};

const UF_LIST = new Set([
  'ac', 'al', 'ap', 'am', 'ba', 'ce', 'df', 'es', 'go', 'ma',
  'mt', 'ms', 'mg', 'pa', 'pb', 'pr', 'pe', 'pi', 'rj', 'rn',
  'rs', 'ro', 'rr', 'sc', 'sp', 'se', 'to'
]);

export function inferCityName(urlString) {
  try {
    const parsed = new URL(urlString);
    const host = parsed.hostname.toLowerCase();
    const parts = host.split('.');
    
    // Ignorar subdomínios comuns
    const filtered = parts.filter(p => !['transparencia', 'portal', 'www', 'gov', 'br', 'pm', 'prefeitura', 'sistemas', 'ecidade'].includes(p));
    const uf = parts.find(p => UF_LIST.has(p));
    
    if (filtered.length > 0) {
      const cityRaw = filtered[0];
      const city = cityRaw.charAt(0).toUpperCase() + cityRaw.slice(1);
      return uf ? `${city} - ${uf.toUpperCase()}` : city;
    }
    return parsed.hostname;
  } catch {
    return 'Município';
  }
}

export function isECidade(urlString) {
  if (!urlString) return false;
  const lower = urlString.toLowerCase();
  return lower.includes('e-cidade') || lower.includes('/contratos/padrao') || lower.includes('ipm.com.br');
}

export function createPortalService({ projectRoot }) {
  const root = path.resolve(projectRoot);
  const configFile = path.join(root, 'data', 'portal_config.json');

  async function get() {
    try {
      const content = await readFile(configFile, 'utf8');
      const data = JSON.parse(content);
      if (data && typeof data.url === 'string' && data.url.trim()) {
        const url = data.url.trim();
        return {
          url,
          name: data.name || inferCityName(url),
          isECidade: isECidade(url),
          custom: true,
        };
      }
    } catch {
      // Arquivo inexistente ou ilegível, usar padrão
    }
    return { ...DEFAULT_PORTAL, custom: false };
  }

  async function set(newConfig) {
    if (!newConfig || typeof newConfig.url !== 'string') {
      throw Object.assign(new Error('URL inválida.'), { status: 400 });
    }
    const rawUrl = newConfig.url.trim();
    try {
      const parsed = new URL(rawUrl);
      if (!['http:', 'https:'].includes(parsed.protocol)) {
        throw new Error();
      }
    } catch {
      throw Object.assign(new Error('Informe uma URL web válida iniciando com https:// ou http://.'), { status: 400 });
    }

    const ecidade = isECidade(rawUrl);
    const cityName = (typeof newConfig.name === 'string' && newConfig.name.trim()) 
      ? newConfig.name.trim() 
      : inferCityName(rawUrl);

    const saved = {
      url: rawUrl,
      name: cityName,
      isECidade: ecidade,
      updated_at: new Date().toISOString(),
    };

    await mkdir(path.dirname(configFile), { recursive: true });
    await writeFile(configFile, JSON.stringify(saved, null, 2), 'utf8');

    return {
      ...saved,
      custom: rawUrl !== DEFAULT_PORTAL.url,
    };
  }

  async function reset() {
    try {
      await writeFile(configFile, JSON.stringify({
        url: DEFAULT_PORTAL.url,
        name: DEFAULT_PORTAL.name,
        isECidade: true,
        updated_at: new Date().toISOString(),
      }, null, 2), 'utf8');
    } catch {
      // Ignorar se não puder salvar
    }
    return { ...DEFAULT_PORTAL, custom: false };
  }

  async function middleware(req, res, next) {
    const url = new URL(req.url, 'http://localhost');
    if (url.pathname !== '/api/portal-config') return next();

    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.setHeader('Cache-Control', 'no-store');
    const reply = (status, value) => {
      res.statusCode = status;
      res.end(JSON.stringify(value));
    };

    if (req.method === 'GET') {
      return reply(200, await get());
    }

    if (req.method === 'POST') {
      let body = '';
      for await (const chunk of req) {
        body += chunk.toString();
        if (body.length > 5000) return reply(413, { error: 'Payload muito grande.' });
      }
      try {
        const payload = JSON.parse(body || '{}');
        if (payload.reset) {
          return reply(200, await reset());
        }
        return reply(200, await set(payload));
      } catch (err) {
        return reply(err.status || 400, { error: err.message || 'Erro ao processar requisição.' });
      }
    }

    return reply(405, { error: 'Método não permitido.' });
  }

  return { get, set, reset, middleware };
}
