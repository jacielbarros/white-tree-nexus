import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { TimelineEntry } from '@app/core/models';
import { TraceabilityTimeline } from './traceability-timeline';

const ENTRIES: TimelineEntry[] = [
  { occurred_at: '2026-06-30T12:00:00Z', kind: 'finding', ref_id: 'f-1', label: 'NC menor', detail: 'Constatação (nc_menor)' },
  { occurred_at: '2026-06-29T12:00:00Z', kind: 'evidence', ref_id: 'ev-1', label: 'Política', detail: 'Evidência (uso_interno, active)' },
];

function apiStub(entries: TimelineEntry[] = ENTRIES, fail = false) {
  return {
    listTimeline: vi.fn((_t: string, _id: string) => (fail ? throwError(() => new Error('x')) : of(entries))),
  };
}

function setup(api: ReturnType<typeof apiStub>): ComponentFixture<TraceabilityTimeline> {
  TestBed.resetTestingModule();
  TestBed.configureTestingModule({
    imports: [TraceabilityTimeline],
    providers: [{ provide: ApiService, useValue: api }],
  });
  const fixture = TestBed.createComponent(TraceabilityTimeline);
  fixture.componentRef.setInput('targetType', 'soa_item');
  fixture.componentRef.setInput('targetId', 'soa-item-1');
  fixture.detectChanges();
  return fixture;
}

describe('TraceabilityTimeline', () => {
  beforeEach(() => TestBed.resetTestingModule());

  it('loads the timeline for the target and renders entries', () => {
    const api = apiStub();
    const fixture = setup(api);
    expect(api.listTimeline).toHaveBeenCalledWith('soa_item', 'soa-item-1');
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('NC menor');
    expect(text).toContain('Constatação'); // kind label
    expect(text).toContain('Política');
  });

  it('shows an empty state when there are no events', () => {
    const fixture = setup(apiStub([]));
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Nenhum evento associado ainda.');
  });

  it('degrades to empty on error without throwing', () => {
    const fixture = setup(apiStub(ENTRIES, true));
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Nenhum evento associado ainda.');
  });
});
