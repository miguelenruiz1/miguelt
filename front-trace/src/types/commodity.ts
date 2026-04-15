/**
 * Commodity discriminator shared by compliance plots/records and inventory
 * products/sales orders. Keep values in sync with the DB CHECK constraints
 * (compliance_plots / compliance_records / entities / sales_orders).
 */
export type CommodityType = 'coffee' | 'cacao' | 'palm' | 'other';

export const COMMODITY_TYPES: CommodityType[] = ['coffee', 'cacao', 'palm', 'other'];

export const COMMODITY_LABEL: Record<CommodityType, string> = {
  coffee: 'Cafe',
  cacao: 'Cacao',
  palm: 'Palma',
  other: 'Otro',
};

export const COMMODITY_COLOR: Record<CommodityType, string> = {
  coffee: 'bg-amber-100 text-amber-800 border-amber-200',
  cacao: 'bg-orange-100 text-orange-800 border-orange-200',
  palm: 'bg-lime-100 text-lime-800 border-lime-200',
  other: 'bg-slate-100 text-slate-700 border-slate-200',
};

export const COMMODITY_ICON: Record<CommodityType, string> = {
  coffee: 'coffee',
  cacao: 'cookie',
  palm: 'palmtree',
  other: 'package',
};

export type RspoTraceModel = 'mass_balance' | 'segregated' | 'identity_preserved';

export const RSPO_TRACE_MODELS: RspoTraceModel[] = [
  'mass_balance',
  'segregated',
  'identity_preserved',
];

export const RSPO_TRACE_MODEL_LABEL: Record<RspoTraceModel, string> = {
  mass_balance: 'Mass Balance',
  segregated: 'Segregated',
  identity_preserved: 'Identity Preserved',
};

export const RSPO_TRACE_MODEL_DESCRIPTION: Record<RspoTraceModel, string> = {
  mass_balance:
    'Mass balance: volumenes certificados y no certificados se mezclan, pero se contabilizan por separado en libros.',
  segregated:
    'Segregated: aceite certificado se mantiene fisicamente separado del no certificado en todos los puntos.',
  identity_preserved:
    'Identity Preserved: mantiene la identidad del molino/plantacion de origen a lo largo de toda la cadena.',
};

export type QualityTestType =
  | 'humidity'
  | 'defects'
  | 'cadmium'
  | 'ffa'
  | 'iv'
  | 'dobi'
  | 'miu'
  | 'lovibond'
  | 'sensory_score'
  | 'other';

export const QUALITY_TEST_TYPES: QualityTestType[] = [
  'humidity',
  'defects',
  'cadmium',
  'ffa',
  'iv',
  'dobi',
  'miu',
  'lovibond',
  'sensory_score',
  'other',
];

export const QUALITY_TEST_LABEL: Record<QualityTestType, string> = {
  humidity: 'Humedad',
  defects: 'Defectos',
  cadmium: 'Cadmio',
  ffa: 'FFA (acidez libre)',
  iv: 'Indice de yodo (IV)',
  dobi: 'DOBI',
  miu: 'MIU',
  lovibond: 'Color Lovibond',
  sensory_score: 'Puntaje sensorial (SCA)',
  other: 'Otro',
};

export const QUALITY_TEST_UNIT: Record<QualityTestType, string> = {
  humidity: '%',
  defects: 'count',
  cadmium: 'mg/kg',
  ffa: '%',
  iv: 'g I2/100g',
  dobi: 'ratio',
  miu: '%',
  lovibond: 'Red',
  sensory_score: 'points',
  other: '',
};
