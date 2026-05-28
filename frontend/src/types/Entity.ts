export interface Entities {
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

export interface GeoEntityDetails {
    uri: string;
    type: string;
    label: string;
    coordinates: {
        lat: number;
        lng: number;
    }
    startDate?: number,
    endDate?: number,
    historical?: string;
    buildingType?: string;
    eventType?: string;
    placeType?: string;
    district?: number;
    address?: string;
    architects?: string[];
    namedAfter?: string[];
    famousInhabitants?: string[];
    events?: string[];
    wikiPage?: string;
    image?: string;
    herisId?: string;
    cultId?: string;
}

export interface InfoEntityDetails {
    uri: string;
    label: string;

    birthDate?: string;
    birthPlace?: string;
    deathDate?: string;
    deathPlace?: string;
    gender?: string;
    image?: string;

    architectOf?: string[];
    residentOf?: string[];
    namedAfter?: string[];

    wikiPage?: string;
}