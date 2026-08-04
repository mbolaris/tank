import type { RenderFrame } from '../../rendering/types';
import type { EntityData, SoccerParticipant } from '../../types/simulation';
import { renderFromCanonical } from './renderFromCanonical';
import { soccerMatchSnapshot } from './fieldGeometry';
import type { PitchTransform } from './usePitchTransform';

export interface SoccerRenderEntity {
    id: number;
    type: 'player' | 'ball';
    x: number;
    y: number;
    fieldX: number;
    fieldY: number;
    radius: number;
    vel_x: number;
    vel_y: number;
    fieldVelX: number;
    fieldVelY: number;
    speed: number;
    team?: 'left' | 'right';
    jersey_number?: number;
    stamina?: number;
    facing?: number;
    has_ball?: boolean;
    genome_data?: EntityData['genome_data'];
    participant?: SoccerParticipant;
}

export interface SoccerScene {
    entities: SoccerRenderEntity[];
}

interface SoccerRenderHint {
    participant_id?: string;
    team?: 'left' | 'right';
    jersey_number?: number;
    stamina?: number;
    facing_angle?: number;
    has_ball?: boolean;
    velocity_x?: number;
    velocity_y?: number;
}

function participantId(entity: EntityData, hint: SoccerRenderHint | undefined): string | undefined {
    return (entity as EntityData & { participant_id?: string }).participant_id ?? hint?.participant_id;
}

export function soccerSceneFromFrame(frame: RenderFrame, transform: PitchTransform): SoccerScene {
    const state = soccerMatchSnapshot(frame.snapshot);
    const participants = new Map((state.participants ?? []).map((participant) => [participant.participant_id, participant]));
    const entities: SoccerRenderEntity[] = [];

    for (const entity of state.entities ?? []) {
        if (entity.type !== 'player' && entity.type !== 'ball') continue;
        const hint = entity.render_hint as SoccerRenderHint | undefined;
        const participant = participants.get(participantId(entity, hint) ?? '');
        const position = renderFromCanonical({ x: entity.x, y: entity.y }, state.coord_space);
        const velocity = renderFromCanonical(
            { x: entity.vel_x ?? hint?.velocity_x ?? 0, y: entity.vel_y ?? hint?.velocity_y ?? 0 },
            state.coord_space,
        );
        const [x, y] = transform.toScreen(position.x, position.y);
        const trueRadius = (entity.radius ?? 0.3) * transform.scale;
        const fieldSpeed = Math.hypot(entity.vel_x ?? hint?.velocity_x ?? 0, entity.vel_y ?? hint?.velocity_y ?? 0);
        const facing = entity.facing ?? hint?.facing_angle;

        // Possession joins the authoritative ball_owner to the participant.
        // Legacy per-entity has_ball is only a fallback for payloads that
        // predate ball_owner - once the field is present (including an
        // explicit null for a loose ball) it is the single source of truth,
        // so exactly one ring is drawn and a loose ball draws none.
        const hasBallOwnerField = state.ball_owner !== undefined;
        const pid = participantId(entity, hint);
        const isBallOwner = hasBallOwnerField
            ? pid !== undefined && pid === state.ball_owner
            : Boolean(entity.has_ball ?? hint?.has_ball);

        entities.push({
            id: entity.id,
            type: entity.type,
            x,
            y,
            fieldX: position.x,
            fieldY: position.y,
            radius: trueRadius,
            vel_x: velocity.x,
            vel_y: velocity.y,
            fieldVelX: entity.vel_x ?? hint?.velocity_x ?? 0,
            fieldVelY: entity.vel_y ?? hint?.velocity_y ?? 0,
            speed: fieldSpeed,
            team: entity.team ?? hint?.team ?? participant?.side,
            jersey_number: entity.jersey_number ?? hint?.jersey_number ?? participant?.uniform_number,
            stamina: entity.stamina ?? hint?.stamina,
            facing: facing === undefined ? undefined : state.coord_space === 'canonical' ? -facing : facing,
            has_ball: entity.type === 'player' ? isBallOwner : false,
            genome_data: entity.genome_data,
            participant,
        });
    }

    return { entities };
}
