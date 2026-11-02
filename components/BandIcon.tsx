import { Eye, ShieldCheck, Siren, TriangleAlert } from "lucide-react";
import type { Band } from "@/lib/types";

const ICONS = { low: ShieldCheck, watch: Eye, high: TriangleAlert, critical: Siren } as const;

export function BandIcon({ band, className }: { band: Band["key"]; className?: string }) {
  const Icon = ICONS[band];
  return <Icon className={className} aria-hidden />;
}
