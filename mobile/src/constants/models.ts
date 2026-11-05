export type ModelRole = "quick_analysis" | "deep_analysis" | "both" | string;

export interface PublicModel {
  name: string;
  display_name: string;
  provider: string;
  capability_level: number;
  roles: ModelRole[];
}

export interface PublicModelsData {
  default_quick_model: string | null;
  default_deep_model: string | null;
  models: PublicModel[];
  quick_models: PublicModel[];
  deep_models: PublicModel[];
}
