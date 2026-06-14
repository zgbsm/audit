export const STAGE_LABELS: Record<string, string> = {
  recon: 'Recon',
  merge: 'Merge Tasks',
  hunt: 'Hunt',
  validate: 'Validate',
  gapfill: 'Gapfill',
  dedupe: 'Dedupe',
  trace: 'Trace',
  feedback: 'Feedback',
  report: 'Report',
};

export const STAGE_ORDER: Record<string, number> = {
  recon: 1,
  merge: 2,
  hunt: 3,
  validate: 4,
  gapfill: 5,
  dedupe: 6,
  trace: 7,
  feedback: 8,
  report: 9,
};

export const POLL_INTERVAL_ACTIVE = 2000;
export const POLL_INTERVAL_INACTIVE = 30000;
