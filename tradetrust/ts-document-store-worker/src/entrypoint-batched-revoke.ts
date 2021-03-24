/* istanbul ignore file */
import { logger } from './logger';
import { getBatchedRevokeEnvConfig } from './config';
import {
  UnprocessedDocuments,
  UnprocessedDocumentsQueue,
  BatchDocuments,
  RevokedDocuments,
  InvalidDocuments
} from './repos';
import {
  connectWallet,
  connectDocumentStore,
} from './document-store';
import { BatchedRevoke } from './tasks';

async function main(){
  const config = getBatchedRevokeEnvConfig();
  const wallet = await connectWallet(config);
  await new BatchedRevoke({
    invalidDocuments: new InvalidDocuments(config),
    unprocessedDocuments: new UnprocessedDocuments(config),
    batchDocuments: new BatchDocuments(config),
    revokedDocuments: new RevokedDocuments(config),
    unprocessedDocumentsQueue: new UnprocessedDocumentsQueue(config),
    wallet: wallet,
    documentStore: await connectDocumentStore(config, wallet),
    messageWaitTime: config.MESSAGE_WAIT_TIME,
    messageVisibilityTimeout: config.MESSAGE_VISIBILITY_TIMEOUT,
    batchSizeBytes: config.BATCH_SIZE_BYTES,
    batchTimeSeconds: config.BATCH_TIME_SECONDS,
    transactionTimeoutSeconds: config.TRANSACTION_TIMEOUT_SECONDS,
    transactionConfirmationThreshold: config.TRANSACTION_CONFIRMATION_THRESHOLD,
    gasPriceMultiplier: config.GAS_PRICE_MULTIPLIER,
    gasPriceLimitGwei: config.GAS_PRICE_LIMIT_GWEI,
    restoreAttempts: config.RESTORE_ATTEMPTS,
    restoreAttemptsIntervalSeconds: config.RESTORE_ATTEMPTS_INTERVAL_SECONDS,
    composeAttempts: config.COMPOSE_ATTEMPTS,
    composeAttemptsIntervalSeconds: config.COMPOSE_ATTEMPTS_INTERVAL_SECONDS,
    revokeAttempts: config.REVOKE_ATTEMPTS,
    revokeAttemptsIntervalSeconds: config.REVOKE_ATTEMPTS_INTERVAL_SECONDS,
    saveAttempts: config.SAVE_ATTEMPTS,
    saveAttemptsIntervalSeconds: config.SAVE_ATTEMPTS_INTERVAL_SECONDS
  }).start();
}

main().catch(logger.error);
