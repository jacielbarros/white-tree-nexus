import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  computed,
  effect,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { ButtonModule } from 'primeng/button';

import {
  PreviewLayout,
  SignatureBlockedArea,
  SignaturePlacementBase,
} from '@app/core/models';

type PdfJsDocument = {
  numPages: number;
  getPage(pageNumber: number): Promise<PdfJsPage>;
};

type PdfJsPage = {
  getViewport(options: { scale: number }): { width: number; height: number };
  render(options: { canvasContext: CanvasRenderingContext2D; viewport: unknown }): { promise: Promise<void> };
};

type PdfJsModule = {
  GlobalWorkerOptions: { workerSrc: string };
  getDocument(options: { data: Uint8Array }): { promise: Promise<PdfJsDocument> };
};

interface SealBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

@Component({
  selector: 'app-pdf-signature-viewer',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ButtonModule],
  template: `
    <section class="pdf-viewer">
      <div class="pdf-viewer__toolbar">
        <div>
          <strong>Preview / Nao assinado</strong>
          <span>Pagina {{ currentPage() }} de {{ pageCount() || 1 }}</span>
        </div>
        <div class="pdf-viewer__actions">
          <p-button icon="pi pi-angle-left" severity="secondary" [disabled]="currentPage() <= 1" (onClick)="previousPage()" />
          <p-button icon="pi pi-angle-right" severity="secondary" [disabled]="currentPage() >= pageCount()" (onClick)="nextPage()" />
          <p-button icon="pi pi-search-minus" severity="secondary" [disabled]="zoom() <= 0.75" (onClick)="zoomOut()" />
          <p-button icon="pi pi-search-plus" severity="secondary" [disabled]="zoom() >= 2" (onClick)="zoomIn()" />
          <p-button label="Confirmar posicao" icon="pi pi-check" [disabled]="!canConfirm()" (onClick)="confirmPlacement()" />
        </div>
      </div>

      @if (loading()) {
        <div class="pdf-viewer__state">Carregando PDF...</div>
      } @else if (error()) {
        <div class="pdf-viewer__state pdf-viewer__state--error">{{ error() }}</div>
      }

      <div class="pdf-viewer__stage">
        <canvas #canvas></canvas>

        @for (area of visibleBlockedAreas(); track area.x_points + ':' + area.y_points + ':' + area.reason) {
          <div class="pdf-viewer__blocked" [style]="blockedAreaStyle(area)" [title]="area.reason || 'Area bloqueada'"></div>
        }

        @if (sealBox(); as box) {
          <div
            class="pdf-viewer__seal"
            [style.left.px]="box.x"
            [style.top.px]="box.y"
            [style.width.px]="box.width"
            [style.height.px]="box.height"
            (pointerdown)="startDrag($event)"
          >
            <strong>Assinatura</strong>
            <span>Arraste para posicionar</span>
            <button type="button" class="pdf-viewer__resize" (pointerdown)="startResize($event)" title="Redimensionar"></button>
          </div>
        }
      </div>
    </section>
  `,
  styles: `
    :host { display: block; }

    .pdf-viewer {
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-md);
      display: grid;
      gap: 10px;
      padding: 10px;
    }

    .pdf-viewer__toolbar {
      align-items: center;
      display: flex;
      gap: 10px;
      justify-content: space-between;
    }

    .pdf-viewer__toolbar div:first-child {
      display: grid;
      gap: 2px;
    }

    .pdf-viewer__toolbar strong {
      color: var(--wtn-text);
      font-size: 13px;
    }

    .pdf-viewer__toolbar span,
    .pdf-viewer__state {
      color: var(--wtn-text-2);
      font-size: 12px;
    }

    .pdf-viewer__actions {
      align-items: center;
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      justify-content: flex-end;
    }

    .pdf-viewer__stage {
      background: var(--wtn-surface);
      border: 1px solid var(--wtn-border);
      min-height: 360px;
      overflow: auto;
      position: relative;
    }

    canvas {
      display: block;
      max-width: none;
    }

    .pdf-viewer__seal {
      align-items: start;
      background: rgba(19, 113, 95, .14);
      border: 2px solid var(--wtn-primary);
      border-radius: 6px;
      color: var(--wtn-text);
      cursor: grab;
      display: grid;
      gap: 2px;
      min-height: 32px;
      min-width: 96px;
      padding: 7px;
      position: absolute;
      touch-action: none;
      user-select: none;
    }

    .pdf-viewer__seal strong {
      font-size: 11px;
      line-height: 1.1;
    }

    .pdf-viewer__seal span {
      color: var(--wtn-text-2);
      font-size: 10px;
      line-height: 1.1;
    }

    .pdf-viewer__resize {
      background: var(--wtn-primary);
      border: 0;
      bottom: -5px;
      cursor: nwse-resize;
      height: 10px;
      padding: 0;
      position: absolute;
      right: -5px;
      width: 10px;
    }

    .pdf-viewer__blocked {
      background: rgba(180, 35, 24, .16);
      border: 1px dashed rgba(180, 35, 24, .8);
      pointer-events: none;
      position: absolute;
    }

    .pdf-viewer__state--error {
      color: var(--wtn-danger);
    }
  `,
})
export class PdfSignatureViewer {
  readonly pdf = input<Blob | null>(null);
  readonly layout = input<PreviewLayout | null>(null);
  readonly placementConfirmed = output<SignaturePlacementBase>();

  private readonly canvas = viewChild<ElementRef<HTMLCanvasElement>>('canvas');
  private pdfDocument: PdfJsDocument | null = null;
  private dragStart: { pointerX: number; pointerY: number; box: SealBox; mode: 'move' | 'resize' } | null = null;

  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly currentPage = signal(1);
  protected readonly pageCount = signal(0);
  protected readonly zoom = signal(1);
  protected readonly sealBox = signal<SealBox | null>(null);

  protected readonly currentMetric = computed(() => {
    const layout = this.layout();
    const page = this.currentPage();
    return layout?.page_metrics.find((metric) => metric.page_number === page) ?? null;
  });

  protected readonly visibleBlockedAreas = computed(() => {
    const layout = this.layout();
    const page = this.currentPage();
    return (layout?.blocked_areas ?? []).filter((area) => area.page === 'all' || area.page === page);
  });

  protected readonly canConfirm = computed(() => Boolean(this.sealBox() && this.currentMetric()));

  constructor() {
    effect(() => {
      const pdf = this.pdf();
      const layout = this.layout();
      if (pdf && layout) {
        void this.loadPdf(pdf, layout);
      }
    });
  }

  protected previousPage(): void {
    if (this.currentPage() > 1) {
      void this.goToPage(this.currentPage() - 1);
    }
  }

  protected nextPage(): void {
    if (this.currentPage() < this.pageCount()) {
      void this.goToPage(this.currentPage() + 1);
    }
  }

  protected zoomIn(): void {
    const placement = this.toCanonicalPlacement();
    this.zoom.update((value) => Math.min(2, value + 0.25));
    void this.renderCurrentPage().then(() => this.applyPlacementAfterZoom(placement));
  }

  protected zoomOut(): void {
    const placement = this.toCanonicalPlacement();
    this.zoom.update((value) => Math.max(0.75, value - 0.25));
    void this.renderCurrentPage().then(() => this.applyPlacementAfterZoom(placement));
  }

  protected startDrag(event: PointerEvent): void {
    const box = this.sealBox();
    if (!box) return;
    event.preventDefault();
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
    this.dragStart = { pointerX: event.clientX, pointerY: event.clientY, box: { ...box }, mode: 'move' };
    window.addEventListener('pointermove', this.onPointerMove);
    window.addEventListener('pointerup', this.onPointerUp, { once: true });
  }

  protected startResize(event: PointerEvent): void {
    const box = this.sealBox();
    if (!box) return;
    event.stopPropagation();
    event.preventDefault();
    this.dragStart = { pointerX: event.clientX, pointerY: event.clientY, box: { ...box }, mode: 'resize' };
    window.addEventListener('pointermove', this.onPointerMove);
    window.addEventListener('pointerup', this.onPointerUp, { once: true });
  }

  protected confirmPlacement(): void {
    const placement = this.toCanonicalPlacement();
    if (placement) {
      this.placementConfirmed.emit(placement);
    }
  }

  protected blockedAreaStyle(area: SignatureBlockedArea): string {
    const metric = this.currentMetric();
    if (!metric) return '';
    const scale = this.canvasScale(metric);
    const top = (metric.height_points - area.y_points - area.height_points) * scale;
    return [
      `left:${area.x_points * scale}px`,
      `top:${top}px`,
      `width:${area.width_points * scale}px`,
      `height:${area.height_points * scale}px`,
    ].join(';');
  }

  private readonly onPointerMove = (event: PointerEvent): void => {
    const start = this.dragStart;
    const metric = this.currentMetric();
    if (!start || !metric) return;
    const dx = event.clientX - start.pointerX;
    const dy = event.clientY - start.pointerY;
    const scale = this.canvasScale(metric);
    const maxWidth = metric.width_points * scale;
    const maxHeight = metric.height_points * scale;
    if (start.mode === 'resize') {
      this.sealBox.set({
        ...start.box,
        width: Math.max(96 * scale, Math.min(maxWidth - start.box.x, start.box.width + dx)),
        height: Math.max(32 * scale, Math.min(maxHeight - start.box.y, start.box.height + dy)),
      });
      return;
    }
    this.sealBox.set({
      ...start.box,
      x: Math.max(0, Math.min(maxWidth - start.box.width, start.box.x + dx)),
      y: Math.max(0, Math.min(maxHeight - start.box.height, start.box.y + dy)),
    });
  };

  private readonly onPointerUp = (): void => {
    this.dragStart = null;
    window.removeEventListener('pointermove', this.onPointerMove);
  };

  private async goToPage(pageNumber: number): Promise<void> {
    this.currentPage.set(pageNumber);
    await this.renderCurrentPage();
    this.resetSealForCurrentPage();
  }

  private applyPlacementAfterZoom(placement: SignaturePlacementBase | null): void {
    const metric = this.currentMetric();
    if (placement && metric) {
      this.applySealFromPlacement(placement, metric);
    }
  }

  private async loadPdf(pdf: Blob, layout: PreviewLayout): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const pdfjs = await import('pdfjs-dist') as PdfJsModule;
      pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.mjs', import.meta.url).toString();
      const bytes = new Uint8Array(await pdf.arrayBuffer());
      this.pdfDocument = await pdfjs.getDocument({ data: bytes }).promise;
      this.pageCount.set(this.pdfDocument.numPages || layout.page_metrics.length || 1);
      this.currentPage.set((layout.latest_placement ?? layout.default_placement).page_number);
      await this.renderCurrentPage();
      this.resetSealForCurrentPage();
    } catch {
      this.error.set('Nao foi possivel carregar o PDF.');
    } finally {
      this.loading.set(false);
    }
  }

  private async renderCurrentPage(): Promise<void> {
    const doc = this.pdfDocument;
    const canvasRef = this.canvas();
    if (!doc || !canvasRef) return;
    const page = await doc.getPage(this.currentPage());
    const viewport = page.getViewport({ scale: this.zoom() });
    const canvas = canvasRef.nativeElement;
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    const context = canvas.getContext('2d');
    if (!context) return;
    await page.render({ canvasContext: context, viewport }).promise;
  }

  private resetSealForCurrentPage(): void {
    const layout = this.layout();
    const metric = this.currentMetric();
    if (!layout || !metric) return;
    this.applySealFromPlacement(this.placementForCurrentPage(layout, metric), metric);
  }

  private placementForCurrentPage(
    layout: PreviewLayout,
    metric: { page_number: number; width_points: number; height_points: number },
  ): SignaturePlacementBase {
    const existing = layout.latest_placement ?? layout.default_placement;
    if (existing.page_number === this.currentPage()) {
      return existing;
    }
    const width = Math.min(existing.width_points, Math.max(96, metric.width_points - 72));
    const height = Math.min(existing.height_points, Math.max(32, metric.height_points - 72));
    return {
      ...existing,
      page_number: metric.page_number,
      x_points: Math.max(0, metric.width_points - width - 36),
      y_points: 36,
      width_points: width,
      height_points: height,
      page_width_points: metric.width_points,
      page_height_points: metric.height_points,
      origin: 'user',
    };
  }

  private applySealFromPlacement(
    placement: SignaturePlacementBase,
    metric: { width_points: number; height_points: number },
  ): void {
    const scale = this.canvasScale(metric);
    this.sealBox.set({
      x: placement.x_points * scale,
      y: (metric.height_points - placement.y_points - placement.height_points) * scale,
      width: placement.width_points * scale,
      height: placement.height_points * scale,
    });
  }

  private canvasScale(metric: { width_points: number }): number {
    const canvas = this.canvas()?.nativeElement;
    if (canvas?.width) {
      return canvas.width / metric.width_points;
    }
    return this.zoom();
  }

  private toCanonicalPlacement(): SignaturePlacementBase | null {
    const metric = this.currentMetric();
    const box = this.sealBox();
    if (!metric || !box) return null;
    const scale = this.canvasScale(metric);
    return {
      page_number: this.currentPage(),
      x_points: Number((box.x / scale).toFixed(2)),
      y_points: Number(((metric.height_points - box.y - box.height) / scale).toFixed(2)),
      width_points: Number((box.width / scale).toFixed(2)),
      height_points: Number((box.height / scale).toFixed(2)),
      page_width_points: metric.width_points,
      page_height_points: metric.height_points,
      coordinate_system: 'pdf_points_bottom_left',
      origin: 'user',
    };
  }
}
