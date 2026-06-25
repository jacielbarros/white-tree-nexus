import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import {
  AssignmentEvent,
  Classification,
  ContextAnalysis,
  Diagnostic,
  DocumentPreview,
  DocumentVersion,
  FormAssignment,
  FormSignature,
  FormTemplate,
  IntegrityVerification,
  Invitation,
  InviteLookup,
  Me,
  MembershipRow,
  Organization,
  PreviewLayout,
  PrintableDocumentType,
  PrintTemplate,
  PrintTemplateVersion,
  Role,
  ScopeStatement,
  SignaturePlacement,
  SignaturePlacementBase,
  SignaturePolicy,
  SignedSignaturePlacement,
  SignedDocument,
  Stakeholder,
  StakeholderMap,
  Suggestion,
  TokenResponse,
} from '@app/core/models';
import { environment } from '@environment/environment';

/** Cliente HTTP único da API. O token e o X-Org-Context são injetados pelo interceptor. */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  // --- Auth ---
  login(email: string, password: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.base}/auth/login`, { email, password });
  }

  logout(): Observable<void> {
    return this.http.post<void>(`${this.base}/auth/logout`, {});
  }

  me(): Observable<Me> {
    return this.http.get<Me>(`${this.base}/me`);
  }

  forgotPassword(email: string): Observable<unknown> {
    return this.http.post(`${this.base}/auth/password/forgot`, { email });
  }

  resetPassword(token: string, password: string): Observable<void> {
    return this.http.post<void>(`${this.base}/auth/password/reset`, { token, password });
  }

  acceptInvite(token: string, fullName?: string, password?: string): Observable<TokenResponse> {
    const body: Record<string, string> = { token };
    if (fullName) {
      body['full_name'] = fullName;
    }
    if (password) {
      body['password'] = password;
    }
    return this.http.post<TokenResponse>(`${this.base}/invitations/accept`, body);
  }

  lookupInvite(token: string): Observable<InviteLookup> {
    return this.http.get<InviteLookup>(`${this.base}/invitations/lookup`, {
      params: { token },
    });
  }

  // --- Organizações ---
  listOrganizations(): Observable<Organization[]> {
    return this.http.get<Organization[]>(`${this.base}/organizations`);
  }

  createOrganization(name: string, slug: string): Observable<Organization> {
    return this.http.post<Organization>(`${this.base}/organizations`, { name, slug });
  }

  changeOrgStatus(orgId: string, action: 'suspend' | 'reactivate'): Observable<Organization> {
    return this.http.patch<Organization>(`${this.base}/organizations/${orgId}/status`, { action });
  }

  // --- Usuários / vínculos (escopados pela org ativa via X-Org-Context) ---
  listUsers(): Observable<MembershipRow[]> {
    return this.http.get<MembershipRow[]>(`${this.base}/users`);
  }

  changeRole(membershipId: string, role: Role): Observable<MembershipRow> {
    return this.http.patch<MembershipRow>(`${this.base}/memberships/${membershipId}/role`, { role });
  }

  unlockUser(userId: string): Observable<void> {
    return this.http.post<void>(`${this.base}/users/${userId}/unlock`, {});
  }

  // --- Convites ---
  listInvitations(): Observable<Invitation[]> {
    return this.http.get<Invitation[]>(`${this.base}/invitations`);
  }

  createInvitation(email: string, role: Role): Observable<Invitation> {
    return this.http.post<Invitation>(`${this.base}/invitations`, { email, role });
  }

  revokeInvitation(invitationId: string): Observable<void> {
    return this.http.post<void>(`${this.base}/invitations/${invitationId}/revoke`, {});
  }

  getDiagnostic(): Observable<Diagnostic> {
    return this.http.get<Diagnostic>(`${this.base}/context/diagnostic`);
  }

  saveDiagnostic(payload: Diagnostic): Observable<Diagnostic> {
    return this.http.put<Diagnostic>(`${this.base}/context/diagnostic`, payload);
  }

  getContextAnalysis(): Observable<ContextAnalysis> {
    return this.http.get<ContextAnalysis>(`${this.base}/context/analysis`);
  }

  saveContextAnalysis(payload: { intended_outcomes: string; methodology?: string | null }): Observable<ContextAnalysis> {
    return this.http.put<ContextAnalysis>(`${this.base}/context/analysis`, payload);
  }

  createContextIssue(payload: Record<string, unknown>): Observable<unknown> {
    return this.http.post(`${this.base}/context/analysis/issues`, payload);
  }

  deleteContextIssue(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/context/analysis/issues/${id}`);
  }

  submitContextAnalysis(): Observable<ContextAnalysis> {
    return this.http.post<ContextAnalysis>(`${this.base}/context/analysis/submit-review`, {});
  }

  approveContextAnalysis(classification: Classification): Observable<DocumentVersion> {
    return this.http.post<DocumentVersion>(`${this.base}/context/analysis/approve`, { classification });
  }

  listContextVersions(): Observable<DocumentVersion[]> {
    return this.http.get<DocumentVersion[]>(`${this.base}/context/analysis/versions`);
  }

  getStakeholderMap(): Observable<StakeholderMap> {
    return this.http.get<StakeholderMap>(`${this.base}/context/stakeholders`);
  }

  createStakeholder(payload: Record<string, unknown>): Observable<Stakeholder> {
    return this.http.post<Stakeholder>(`${this.base}/context/stakeholders`, payload);
  }

  getScope(): Observable<ScopeStatement> {
    return this.http.get<ScopeStatement>(`${this.base}/context/scope`);
  }

  saveScope(payload: Record<string, unknown>): Observable<ScopeStatement> {
    return this.http.put<ScopeStatement>(`${this.base}/context/scope`, payload);
  }

  createScopeItem(payload: Record<string, unknown>): Observable<unknown> {
    return this.http.post(`${this.base}/context/scope/items`, payload);
  }

  getContextOverview(): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(`${this.base}/context/overview`);
  }

  listSuggestions(): Observable<Suggestion[]> {
    return this.http.get<Suggestion[]>(`${this.base}/context/suggestions`);
  }

  acceptSuggestion(suggestionId: string): Observable<unknown> {
    return this.http.post(`${this.base}/context/suggestions/accept`, { suggestion_id: suggestionId });
  }

  // --- Templates de formulário ---
  listTemplates(): Observable<FormTemplate[]> {
    return this.http.get<FormTemplate[]>(`${this.base}/form-templates`);
  }

  createTemplate(payload: { kind: string; title: string; schema: unknown[] }): Observable<FormTemplate> {
    return this.http.post<FormTemplate>(`${this.base}/form-templates`, payload);
  }

  updateTemplate(id: string, payload: Partial<{ title: string; schema: unknown[]; status: string }>): Observable<FormTemplate> {
    return this.http.patch<FormTemplate>(`${this.base}/form-templates/${id}`, payload);
  }

  deleteTemplate(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/form-templates/${id}`);
  }

  // --- Atribuições ---
  listAssignments(): Observable<FormAssignment[]> {
    return this.http.get<FormAssignment[]>(`${this.base}/form-assignments`);
  }

  createAssignment(payload: {
    template_id: string;
    respondent_user_id?: string | null;
    respondent_email?: string | null;
    deadline_at?: string | null;
    instructions?: string | null;
  }): Observable<FormAssignment> {
    return this.http.post<FormAssignment>(`${this.base}/form-assignments`, payload);
  }

  getAssignment(id: string): Observable<FormAssignment> {
    return this.http.get<FormAssignment>(`${this.base}/form-assignments/${id}`);
  }

  claimAssignment(id: string): Observable<FormAssignment> {
    return this.http.post<FormAssignment>(`${this.base}/form-assignments/${id}/claim`, {});
  }

  saveAnswers(id: string, answers: Record<string, unknown>): Observable<FormAssignment> {
    return this.http.put<FormAssignment>(`${this.base}/form-assignments/${id}/answers`, { answers });
  }

  submitAssignment(id: string): Observable<FormAssignment> {
    return this.http.post<FormAssignment>(`${this.base}/form-assignments/${id}/submit`, {});
  }

  returnAssignment(id: string, reason: string): Observable<FormAssignment> {
    return this.http.post<FormAssignment>(`${this.base}/form-assignments/${id}/return`, { reason });
  }

  cancelAssignment(id: string): Observable<FormAssignment> {
    return this.http.post<FormAssignment>(`${this.base}/form-assignments/${id}/cancel`, {});
  }

  remindAssignment(id: string): Observable<void> {
    return this.http.post<void>(`${this.base}/form-assignments/${id}/remind`, {});
  }

  signAssignment(id: string): Observable<FormSignature> {
    return this.http.post<FormSignature>(`${this.base}/form-assignments/${id}/sign`, {});
  }

  getAssignmentEvents(id: string): Observable<AssignmentEvent[]> {
    return this.http.get<AssignmentEvent[]>(`${this.base}/form-assignments/${id}/events`);
  }

  getAssignmentSignatures(id: string): Observable<FormSignature[]> {
    return this.http.get<FormSignature[]>(`${this.base}/form-assignments/${id}/signatures`);
  }

  verifyAssignment(id: string): Observable<{ valid: boolean; content_hash: string }> {
    return this.http.get<{ valid: boolean; content_hash: string }>(`${this.base}/form-assignments/${id}/verify`);
  }

  // --- Política de assinatura ---
  getSignaturePolicy(): Observable<SignaturePolicy> {
    return this.http.get<SignaturePolicy>(`${this.base}/form-signature-policy`);
  }

  updateSignaturePolicy(payload: SignaturePolicy): Observable<SignaturePolicy> {
    return this.http.put<SignaturePolicy>(`${this.base}/form-signature-policy`, payload);
  }

  // --- Documentos imprimiveis/assinaveis ---
  listPrintTemplates(documentType?: PrintableDocumentType): Observable<PrintTemplate[]> {
    return this.http.get<PrintTemplate[]>(`${this.base}/print-documents/templates`, {
      params: documentType ? { document_type: documentType } : {},
    });
  }

  createPrintTemplate(payload: {
    document_type: PrintableDocumentType;
    name: string;
    description?: string | null;
    default_classification?: string;
  }): Observable<PrintTemplate> {
    return this.http.post<PrintTemplate>(`${this.base}/print-documents/templates`, payload);
  }

  createPrintTemplateVersion(
    templateId: string,
    payload: {
      layout_schema: Record<string, unknown>;
      allowed_variables: Record<string, unknown>;
      required_sections: string[];
    },
  ): Observable<PrintTemplateVersion> {
    return this.http.post<PrintTemplateVersion>(
      `${this.base}/print-documents/templates/${templateId}/versions`,
      payload,
    );
  }

  activatePrintTemplateVersion(templateId: string, versionId: string): Observable<PrintTemplate> {
    return this.http.post<PrintTemplate>(
      `${this.base}/print-documents/templates/${templateId}/versions/${versionId}/activate`,
      {},
    );
  }

  createDocumentPreview(payload: {
    document_type: PrintableDocumentType;
    source_artifact_id?: string | null;
    template_version_id?: string | null;
    classification?: string | null;
  }): Observable<DocumentPreview> {
    return this.http.post<DocumentPreview>(`${this.base}/print-documents/previews`, payload);
  }

  getDocumentPreview(previewId: string): Observable<DocumentPreview> {
    return this.http.get<DocumentPreview>(`${this.base}/print-documents/previews/${previewId}`);
  }

  downloadPreviewPdf(previewId: string): Observable<Blob> {
    return this.http.get(`${this.base}/print-documents/previews/${previewId}/pdf`, {
      responseType: 'blob',
    });
  }

  openPreviewInlinePdf(previewId: string): Observable<Blob> {
    return this.http.get(`${this.base}/print-documents/previews/${previewId}/inline-pdf`, {
      responseType: 'blob',
    });
  }

  getPreviewLayout(previewId: string): Observable<PreviewLayout> {
    return this.http.get<PreviewLayout>(`${this.base}/print-documents/previews/${previewId}/layout`);
  }

  listSignaturePlacements(previewId: string): Observable<SignaturePlacement[]> {
    return this.http.get<SignaturePlacement[]>(`${this.base}/print-documents/previews/${previewId}/signature-placements`);
  }

  confirmSignaturePlacement(
    previewId: string,
    placement: SignaturePlacementBase,
    snapshotHash: string,
  ): Observable<SignaturePlacement> {
    return this.http.post<SignaturePlacement>(`${this.base}/print-documents/previews/${previewId}/signature-placements`, {
      ...placement,
      confirm_snapshot_hash: snapshotHash,
    });
  }

  signDocumentPreview(
    previewId: string,
    snapshotHash?: string,
    confirmedPlacementId?: string | null,
  ): Observable<SignedDocument> {
    const body: Record<string, string | null> = {
      confirm_snapshot_hash: snapshotHash ?? null,
    };
    if (confirmedPlacementId) {
      body['confirmed_placement_id'] = confirmedPlacementId;
    }
    return this.http.post<SignedDocument>(`${this.base}/print-documents/previews/${previewId}/sign`, body);
  }

  listSignedDocuments(
    documentType?: PrintableDocumentType,
    sourceArtifactId?: string | null,
  ): Observable<SignedDocument[]> {
    const params: Record<string, string> = {};
    if (documentType) {
      params['document_type'] = documentType;
    }
    if (sourceArtifactId) {
      params['source_artifact_id'] = sourceArtifactId;
    }
    return this.http.get<SignedDocument[]>(`${this.base}/print-documents/signed`, { params });
  }

  downloadSignedPdf(documentId: string): Observable<Blob> {
    return this.http.get(`${this.base}/print-documents/signed/${documentId}/pdf`, {
      responseType: 'blob',
    });
  }

  verifySignedDocument(documentId: string): Observable<IntegrityVerification> {
    return this.http.post<IntegrityVerification>(`${this.base}/print-documents/signed/${documentId}/verify`, {});
  }

  getSignedSignaturePlacement(documentId: string): Observable<SignedSignaturePlacement | null> {
    return this.http.get<SignedSignaturePlacement | null>(
      `${this.base}/print-documents/signed/${documentId}/signature-placement`,
    );
  }

  // --- Atalhos genéricos (para módulos sem métodos nomeados no service) ---
  get<T>(path: string, params?: Record<string, string>): Observable<T> {
    return this.http.get<T>(`${this.base}${path}`, params ? { params } : {});
  }

  post<T>(path: string, body: unknown): Observable<T> {
    return this.http.post<T>(`${this.base}${path}`, body);
  }

  postForm<T>(path: string, body: FormData): Observable<T> {
    return this.http.post<T>(`${this.base}${path}`, body);
  }

  put<T>(path: string, body: unknown): Observable<T> {
    return this.http.put<T>(`${this.base}${path}`, body);
  }

  patch<T>(path: string, body: unknown): Observable<T> {
    return this.http.patch<T>(`${this.base}${path}`, body);
  }

  delete<T>(path: string, body?: unknown): Observable<T> {
    return this.http.delete<T>(`${this.base}${path}`, body === undefined ? {} : { body });
  }

  /** Download binário (ex.: exportação de PDF). */
  getBlob(path: string): Observable<Blob> {
    return this.http.get(`${this.base}${path}`, { responseType: 'blob' });
  }

  // --- Respondente externo (sem auth) ---
  getFormByToken(token: string): Observable<FormAssignment> {
    return this.http.get<FormAssignment>(`${this.base}/forms/respond/${token}`);
  }

  claimByToken(token: string): Observable<FormAssignment> {
    return this.http.post<FormAssignment>(`${this.base}/forms/respond/${token}/claim`, {});
  }

  saveAnswersByToken(token: string, answers: Record<string, unknown>): Observable<FormAssignment> {
    return this.http.put<FormAssignment>(`${this.base}/forms/respond/${token}/answers`, { answers });
  }

  submitByToken(token: string): Observable<FormAssignment> {
    return this.http.post<FormAssignment>(`${this.base}/forms/respond/${token}/submit`, {});
  }

  requestOtpByToken(token: string): Observable<void> {
    return this.http.post<void>(`${this.base}/forms/respond/${token}/otp`, {});
  }

  signByToken(token: string, otp: string, signerName: string): Observable<FormSignature> {
    return this.http.post<FormSignature>(`${this.base}/forms/respond/${token}/sign`, {
      otp,
      signer_name: signerName,
    });
  }
}
