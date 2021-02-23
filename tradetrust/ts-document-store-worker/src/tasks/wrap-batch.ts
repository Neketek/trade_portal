import { wrapDocuments } from '@govtechsg/open-attestation';
import { logger } from '../logger';
import { Batch } from './data';
import { Task } from './interfaces';


class WrapBatch implements Task<void>{
  private batch: Batch;
  constructor({
    batch
  }:{
    batch: Batch
  }){
    this.batch = batch;
  }

  prepareBatchUnwrappedDocumentsData(){
    logger.debug('prepareBatchUnwrappedDocumentsData');
    const keys:Array<string> = new Array<string>(this.batch.unwrappedDocuments.size);
    const bodies: Array<any> = new Array<any>(this.batch.unwrappedDocuments.size);
    let documentIndex = 0;
    for(let [key, entry] of this.batch.unwrappedDocuments){
      keys[documentIndex] = key;
      bodies[documentIndex] = entry.body;
      documentIndex++;
    }
    return {keys, bodies};
  }

  next(){
    logger.debug('next');
    let {keys, bodies} = this.prepareBatchUnwrappedDocumentsData();
    bodies = wrapDocuments(bodies);
    this.batch.wrappedDocuments.clear();
    // size here is irrelevant therefore we're not computing it
    keys.forEach((key, index)=>{this.batch.wrappedDocuments.set(key, {body: bodies[index], size: 0})});
    this.batch.merkleRoot = bodies[0].signature.merkleRoot;
    this.batch.wrapped = true;
  }

  start(){
    logger.debug('start');
    logger.info('Started documents wrapping...')
    this.next();
    logger.info(
      'Completed documents wrapping. Documents count = %s, merkleRoot = %s',
      this.batch.wrappedDocuments.size,
      this.batch.merkleRoot
    );
  }
}

export default WrapBatch;
