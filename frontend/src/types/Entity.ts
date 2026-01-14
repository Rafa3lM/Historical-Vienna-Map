export interface EntitiesDto {
  count: string,
  entities: Entity[]
}

export interface Entity {
  uri: string;
  type: string;
  label: string;
  lat: number;
  lng: number;
  startDate?: number,
  endDate?: number,
  historical?: string;
}
