IBAN_ALLOWED_COUNTRIES = ['CH', 'LI']
QR_IID = {"start": 30000, "end": 31999}
AMOUNT_REGEX = r'^\d{1,9}\.\d{2}$'
DATE_REGEX = r'(\d{4})-(\d{2})-(\d{2})'
MM_TO_UU = 3.543307
BILL_HEIGHT = '105mm'
RECEIPT_WIDTH = '62mm'
PAYMENT_WIDTH = '148mm'
MAX_CHARS_PAYMENT_LINE = 72
MAX_CHARS_RECEIPT_LINE = 38
A4 = ('210mm', '297mm')

# Annex D: Multilingual headings
LABELS = {
    'Payment part': {
        'de': 'Zahlteil',
        'fr': 'Section paiement',
        'it': 'Sezione pagamento'
    },
    'Account / Payable to': {
        'de': 'Konto / Zahlbar an',
        'fr': 'Compte / Payable à',
        'it': 'Conto / Pagabile a',
    },
    'Reference': {'de': 'Referenz', 'fr': 'Référence', 'it': 'Riferimento'},
    'Additional information': {
        'de': 'Zusätzliche Informationen',
        'fr': 'Informations supplémentaires',
        'it': 'Informazioni supplementari',
    },
    'Currency': {'de': 'Währung', 'fr': 'Monnaie', 'it': 'Valuta'},
    'Amount': {'de': 'Betrag', 'fr': 'Montant', 'it': 'Importo'},
    'Receipt': {'de': 'Empfangsschein', 'fr': 'Récépissé', 'it': 'Ricevuta'},
    'Acceptance point': {
        'de': 'Annahmestelle',
        'fr': 'Point de dépôt',
        'it': 'Punto di accettazione'
    },
    'Separate before paying in': {
        'de': 'Vor der Einzahlung abzutrennen',
        'fr': 'A détacher avant le versement',
        'it': 'Da staccare prima del versamento',
    },
    'Payable by': {
        'de': 'Zahlbar durch',
        'fr': 'Payable par',
        'it': 'Pagabile da'
    },
    'Payable by (name/address)': {
        'de': 'Zahlbar durch (Name/Adresse)',
        'fr': 'Payable par (nom/adresse)',
        'it': 'Pagabile da (nome/indirizzo)',
    },
    # The extra ending space allows to differentiate from the other 'Payable by' above.
    'Payable by ': {
        'de': 'Zahlbar bis',
        'fr': 'Payable jusqu’au',
        'it': 'Pagabile fino al'
    },
    'In favour of': {
        'de': 'Zugunsten',
        'fr': 'En faveur de',
        'it': 'A favore di'
    },
}
SCISSORS_SVG_PATH = (
    'm 0.764814,4.283977 c 0.337358,0.143009 0.862476,-0.115279 0.775145,-0.523225 -0.145918,-0.497473 '
    '-0.970289,-0.497475 -1.116209,-2e-6 -0.0636,0.23988 0.128719,0.447618 0.341064,0.523227 z m 3.875732,-1.917196 '
    'c 1.069702,0.434082 2.139405,0.868164 3.209107,1.302246 -0.295734,0.396158 -0.866482,0.368049 -1.293405,0.239509 '
    '-0.876475,-0.260334 -1.71099,-0.639564 -2.563602,-0.966653 -0.132426,-0.04295 -0.265139,-0.124595 '
    '-0.397393,-0.144327 -0.549814,0.22297 -1.09134,0.477143 -1.667719,0.62213 -0.07324,0.232838 0.150307,0.589809 '
    '-0.07687,0.842328 -0.311347,0.532157 -1.113542,0.624698 -1.561273,0.213165 -0.384914,-0.301216 '
    '-0.379442,-0.940948 7e-6,-1.245402 0.216628,-0.191603 0.506973,-0.286636 0.794095,-0.258382 0.496639,0.01219 '
    '1.013014,-0.04849 1.453829,-0.289388 0.437126,-0.238777 0.07006,-0.726966 -0.300853,-0.765416 '
    '-0.420775,-0.157424 -0.870816,-0.155853 -1.312747,-0.158623 -0.527075,-0.0016 -1.039244,-0.509731 '
    '-0.904342,-1.051293 0.137956,-0.620793 0.952738,-0.891064 1.47649,-0.573851 0.371484,0.188118 '
    '0.594679,0.675747 0.390321,1.062196 0.09829,0.262762 0.586716,0.204086 0.826177,0.378204 0.301582,0.119237 '
    '0.600056,0.246109 0.899816,0.36981 0.89919,-0.349142 1.785653,-0.732692 2.698347,-1.045565 0.459138,-0.152333 '
    '1.033472,-0.283325 1.442046,0.05643 0.217451,0.135635 -0.06954,0.160294 -0.174725,0.220936 -0.979101,0.397316 '
    '-1.958202,0.794633 -2.937303,1.19195 z m -3.44165,-1.917196 c -0.338434,-0.14399 -0.861225,0.116943 '
    '-0.775146,0.524517 0.143274,0.477916 0.915235,0.499056 1.10329,0.04328 0.09674,-0.247849 -0.09989,-0.490324 '
    '-0.328144,-0.567796 z'
)