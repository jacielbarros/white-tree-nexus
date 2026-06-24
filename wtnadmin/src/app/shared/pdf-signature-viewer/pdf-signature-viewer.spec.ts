import { ComponentFixture, TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';

import { PreviewLayout } from '@app/core/models';
import { PdfSignatureViewer } from './pdf-signature-viewer';

const LAYOUT: PreviewLayout = {
  preview_id: 'preview-1',
  document_type: 'gap_report',
  snapshot_hash: 'a'.repeat(64),
  page_metrics: [{ page_number: 1, width_points: 842, height_points: 595, rotation: 0 }],
  blocked_areas: [{ page: 1, x_points: 0, y_points: 0, width_points: 100, height_points: 40, reason: 'Rodape' }],
  default_placement: {
    page_number: 1,
    x_points: 626,
    y_points: 36,
    width_points: 180,
    height_points: 54,
    page_width_points: 842,
    page_height_points: 595,
    coordinate_system: 'pdf_points_bottom_left',
    origin: 'default',
  },
  latest_placement: null,
};

describe('PdfSignatureViewer', () => {
  let fixture: ComponentFixture<PdfSignatureViewer>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PdfSignatureViewer],
    }).compileComponents();

    fixture = TestBed.createComponent(PdfSignatureViewer);
    fixture.componentRef.setInput('layout', LAYOUT);
    fixture.detectChanges();
  });

  it('renders preview status and controls', () => {
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Preview / Nao assinado');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Pagina 1');
  });

  it('keeps blocked areas visible for the current page', () => {
    const component = fixture.componentInstance as unknown as {
      visibleBlockedAreas(): unknown[];
    };

    expect(component.visibleBlockedAreas().length).toBe(1);
  });

  it('converts the visual seal to canonical PDF coordinates', () => {
    let emitted: unknown;
    fixture.componentInstance.placementConfirmed.subscribe((value) => {
      emitted = value;
    });

    const component = fixture.componentInstance as unknown as {
      sealBox: { set(value: { x: number; y: number; width: number; height: number }): void };
      confirmPlacement(): void;
    };
    const canvas = (fixture.nativeElement as HTMLElement).querySelector('canvas') as HTMLCanvasElement;
    canvas.width = 842;
    canvas.height = 595;
    component.sealBox.set({ x: 626, y: 505, width: 180, height: 54 });
    component.confirmPlacement();

    expect(emitted).toMatchObject({
      page_number: 1,
      x_points: 626,
      y_points: 36,
      width_points: 180,
      height_points: 54,
      coordinate_system: 'pdf_points_bottom_left',
    });
  });

  it('supports page navigation and zoom controls without changing canonical coordinates', () => {
    const component = fixture.componentInstance as unknown as {
      currentPage: { (): number; set(value: number): void };
      pageCount: { set(value: number): void };
      zoom: { (): number };
      nextPage(): void;
      previousPage(): void;
      zoomIn(): void;
      zoomOut(): void;
    };

    component.pageCount.set(2);
    component.nextPage();
    expect(component.currentPage()).toBe(2);

    component.previousPage();
    expect(component.currentPage()).toBe(1);

    component.zoomIn();
    expect(component.zoom()).toBe(1.25);

    component.zoomOut();
    expect(component.zoom()).toBe(1);
  });

  it('moves the seal inside the current page bounds', () => {
    const canvas = (fixture.nativeElement as HTMLElement).querySelector('canvas') as HTMLCanvasElement;
    canvas.width = 842;
    canvas.height = 595;

    const component = fixture.componentInstance as unknown as {
      dragStart: { pointerX: number; pointerY: number; box: { x: number; y: number; width: number; height: number }; mode: 'move' } | null;
      sealBox: {
        (): { x: number; y: number; width: number; height: number } | null;
        set(value: { x: number; y: number; width: number; height: number }): void;
      };
      onPointerMove(event: PointerEvent): void;
    };

    component.sealBox.set({ x: 626, y: 505, width: 180, height: 54 });
    component.dragStart = {
      pointerX: 10,
      pointerY: 10,
      box: { x: 626, y: 505, width: 180, height: 54 },
      mode: 'move',
    };
    component.onPointerMove({ clientX: 40, clientY: 20 } as PointerEvent);

    expect(component.sealBox()).toMatchObject({ x: 656, y: 515, width: 180, height: 54 });
  });
});
