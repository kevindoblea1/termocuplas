import { EventLog } from '../types';
import './EventsList.css';

interface EventsListProps {
  events: EventLog[];
}

const severityColors: Record<EventLog['severity'], string> = {
  INFO: '#0f172a',
  WARNING: '#92400e',
  ERROR: '#991b1b',
};

export function EventsList({ events }: EventsListProps) {
  return (
    <div className="events">
      <h2>Registro de eventos</h2>
      <ul>
        {events.map((event) => (
          <li key={event.id}>
            <span className="events__timestamp">
              {new Date(event.ts).toLocaleTimeString()}
            </span>
            <span className="events__code" style={{ color: severityColors[event.severity] }}>
              {event.code}
            </span>
            <span className="events__message">{event.message}</span>
          </li>
        ))}
        {events.length === 0 && <li className="events__empty">Sin eventos recientes.</li>}
      </ul>
    </div>
  );
}
