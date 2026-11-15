"""Shared constants: TLD risk, registrar risk, CMS signatures, etc."""

TLD_RISK = {
    'high': {'top', 'xyz', 'icu', 'tk', 'ml', 'ga', 'cf', 'gq', 'buzz', 'surf', 'click', 'link', 'fun', 'monster', 'rest', 'cam'},
    'medium': {'io', 'co', 'me', 'cc', 'ws', 'biz', 'info', 'online', 'site', 'store', 'shop', 'live', 'space', 'tech', 'website', 'solutions', 'digital', 'agency', 'dev', 'app'},
    'low': {'com', 'org', 'net', 'edu', 'gov', 'ru', 'uk', 'de', 'fr', 'jp', 'us', 'ca', 'au', 'nl', 'se', 'no', 'fi', 'dk', 'it', 'es', 'pl', 'cz', 'at', 'ch', 'be'},
}

HIGH_RISK_REGISTRARS = {
    'gname', 'namesilo', 'alpnames', 'regru-ru', 'pdr ltd', 'nicenic', 'west263',
    'todaynic', 'jiangsu bangning', 'epik', 'hosting concepts', 'alibaba',
}

LOW_RISK_REGISTRARS = {
    'godaddy', 'namecheap', 'cloudflare', 'google', 'amazon', 'tucows',
    'gandi', 'ovh', 'enom', 'network solutions', 'markmonitor', 'safenames',
    'csc corporate domains', 'reg.ru',
}

PRIVACY_PROVIDERS = {
    'whoisguard', 'privacyprotect', 'domains by proxy', 'contact privacy',
    'withheld for privacy', 'redacted for privacy', 'data protected',
    'privacy service', 'whois privacy', 'identity protection', 'perfect privacy',
}

CMS_SIGNATURES = {
    'WordPress': ['/wp-content/', '/wp-includes/', 'wp-json', 'wp-embed.min.js'],
    'Tilda': ['tilda.cc', 'tildacdn.com', 'tilda-blocks'],
    'Bitrix': ['/bitrix/', 'BX.ready', 'bitrix/js'],
    'Joomla': ['/media/jui/', '/components/com_', 'Joomla!'],
    'Shopify': ['cdn.shopify.com', 'Shopify.theme', 'shopify-section'],
    'Wix': ['static.wixstatic.com', '_wix_browser_sess', 'wix-code-sdk'],
    'Squarespace': ['squarespace.com', 'squarespace-cdn'],
    'Drupal': ['Drupal.settings', '/sites/default/files/'],
    'OpenCart': ['catalog/view/theme', 'route=common'],
    'PrestaShop': ['prestashop', '/themes/default-bootstrap'],
}

FRAMEWORK_SIGNATURES = {
    'Next.js': ['__NEXT_DATA__', '_next/static', 'next/head'],
    'React': ['_reactRootContainer', 'react-root', 'data-reactroot'],
    'Vue.js': ['__vue__', 'data-v-', 'Vue.config'],
    'Angular': ['ng-version', 'ng-app', 'angular.min.js'],
    'Svelte': ['__svelte'],
    'Nuxt': ['__NUXT__', '_nuxt/'],
}

PAYMENT_SIGNATURES = {
    'Stripe': ['js.stripe.com', 'Stripe(', 'stripe-js'],
    'YooKassa': ['yookassa.ru', 'kassa.yandex.ru', 'checkout-widget'],
    'CloudPayments': ['widget.cloudpayments.ru', 'CloudPayments'],
    'Tinkoff': ['securepay.tinkoff.ru'],
    'SberPay': ['securepayments.sberbank.ru'],
    'PayPal': ['paypal.com/sdk', 'paypal-button'],
    'NowPayments': ['nowpayments.io'],
    'Cryptomus': ['cryptomus.com'],
}

CHAT_SIGNATURES = {
    'Intercom': ['intercom.io', 'intercomSettings'],
    'Tawk.to': ['tawk.to', 'Tawk_API'],
    'Jivo': ['jivo.ru', 'jivosite.com', 'jivo_api'],
    'Tidio': ['tidio.co', 'tidioChatApi'],
    'Carrot': ['carrotquest.io'],
    'LiveChat': ['livechatinc.com'],
}

GENERIC_MX_PROVIDERS = {
    'google': ['google.com', 'googlemail.com', 'gmail-smtp'],
    'yandex': ['yandex.ru', 'yandex.net'],
    'mail.ru': ['mail.ru', 'mxs.mail.ru'],
    'outlook': ['outlook.com', 'protection.outlook.com'],
    'zoho': ['zoho.com', 'zoho.eu'],
    'proton': ['protonmail.ch', 'proton.me'],
}

SECURITY_HEADERS = [
    'strict-transport-security',
    'content-security-policy',
    'x-frame-options',
    'x-content-type-options',
    'referrer-policy',
    'permissions-policy',
]

LEGAL_PATHS = {
    'tos': ['/terms', '/tos', '/terms-of-service', '/agreement', '/conditions', '/terms-and-conditions', '/legal', '/legal/terms', '/en/terms', '/terms-of-use', '/user-agreement', '/eula'],
    'privacy': ['/privacy', '/privacy-policy', '/data-protection', '/privacypolicy', '/legal/privacy', '/en/privacy', '/privacy-notice'],
    'aml': ['/aml', '/kyc', '/anti-money-laundering'],
    'cookies': ['/cookies', '/cookie-policy'],
    'refund': ['/refund', '/returns', '/refund-policy', '/return-policy'],
    'contacts': ['/contacts', '/contact', '/contact-us', '/about', '/about-us', '/en/about'],
}

COMPANY_PATTERNS = [
    r'\b(?:LLC|Ltd\.?|Inc\.?|Corp\.?|GmbH|S\.?A\.?|B\.?V\.?|PLC|LLP|SE)\b',
    r'\b(?:ООО|ОАО|ЗАО|ПАО|АО|ИП)\s*[«"\']?[\w\s\-]+[»"\']?',
]

REG_NUMBER_PATTERNS = [
    r'HE\s?\d{5,7}',
    r'ИНН\s?\d{10,12}',
    r'ОГРН\s?\d{13,15}',
    r'Reg\.?\s*(?:No\.?|Number)\s*:?\s*[\d\-]+',
    r'Company\s*(?:No\.?|Number)\s*:?\s*[\d\-]+',
]

LICENSE_PATTERNS = [
    r'MGA/[A-Z]/\d+/\d+',
    r'Curacao\s+(?:e-?Gaming|license)',
    r'UKGC\s*\d+',
    r'FCA\s*\d+',
]

JURISDICTION_KEYWORDS = {
    'Cyprus': ['cyprus', 'nicosia', 'limassol', 'кипр'],
    'Curacao': ['curacao', 'curaçao', 'кюрасао'],
    'Malta': ['malta', 'мальта', 'valletta'],
    'BVI': ['british virgin islands', 'bvi'],
    'Estonia': ['estonia', 'tallinn', 'эстония'],
    'UK': ['united kingdom', 'england', 'london', 'великобритания'],
    'Seychelles': ['seychelles', 'сейшелы'],
    'Belize': ['belize', 'белиз'],
    'Anjouan': ['anjouan', 'comoros', 'анжуан'],
    'Gibraltar': ['gibraltar', 'гибралтар'],
    'Isle of Man': ['isle of man'],
}
