from transformers import pipeline
import os
import yaml
from openagents_service_provider_proto import rpc_pb2_grpc
from openagents_service_provider_proto import rpc_pb2
import time
import grpc

class Translator:
    FLORES_MAPPING = {'en': 'eng_Latn', 'ceb': 'ceb_Latn', 'de': 'deu_Latn', 'sv': 'swe_Latn', 'fr': 'fra_Latn', 'nl': 'nld_Latn', 'ru': 'rus_Cyrl', 'es': 'spa_Latn',
                  'it': 'ita_Latn', 'pl': 'pol_Latn', 'ja': 'jpn_Jpan', 'zh': 'zho_Hans', 'uk': 'ukr_Cyrl', 'vi': 'vie_Latn', 'ar': 'arb_Arab',
                  'pt': 'por_Latn', 'fa': 'pes_Arab', 'ca': 'cat_Latn', 'sr': 'srp_Cyrl', 'id': 'ind_Latn', 'ko': 'kor_Hang', 'no': 'nob_Latn',
                  'fi': 'fin_Latn', 'tr': 'tur_Latn', 'cs': 'ces_Latn', 'hu': 'hun_Latn', 'ro': 'ron_Latn', 'eu': 'eus_Latn', 'ms': 'zsm_Latn',
                  'eo': 'epo_Latn', 'he': 'heb_Hebr', 'hy': 'hye_Armn', 'da': 'dan_Latn', 'bg': 'bul_Cyrl', 'cy': 'cym_Latn', 'sk': 'slk_Latn',
                  'uz': 'uzn_Latn', 'et': 'est_Latn', 'be': 'bel_Cyrl', 'kk': 'kaz_Cyrl', 'el': 'ell_Grek', 'lt': 'lit_Latn', 'gl': 'glg_Latn',
                  'ur': 'urd_Arab', 'az': 'azj_Latn', 'sl': 'slv_Latn', 'ka': 'kat_Geor', 'hi': 'hin_Deva', 'th': 'tha_Thai', 'ta': 'tam_Taml',
                  'bn': 'ben_Beng', 'mk': 'mkd_Cyrl',  'lv': 'lvs_Latn', 'af': 'afr_Latn', 'tg': 'tgk_Cyrl', 'my': 'mya_Mymr',
                  'mg': 'plt_Latn', 'sq': 'als_Latn', 'mr': 'mar_Deva', 'te': 'tel_Telu', 'ml': 'mal_Mlym', 'ky': 'kir_Cyrl', 'sw': 'swh_Latn',
                  'jv': 'jav_Latn', 'ht': 'hat_Latn', 'lb': 'ltz_Latn', 'su': 'sun_Latn', 'ku': 'kmr_Latn', 'ga': 'gle_Latn', 'is': 'isl_Latn',
                  'fy': 'fao_Latn', 'pa': 'pan_Guru', 'yo': 'yor_Latn', 'ne': 'npi_Deva', 'ha': 'hau_Latn', 'kn': 'kan_Knda', 'gu': 'guj_Gujr',
                  'mn': 'khk_Cyrl', 'ig': 'ibo_Latn', 'si': 'sin_Sinh', 'ps': 'pbt_Arab', 'gd': 'gla_Latn', 'sd': 'snd_Arab', 'yi': 'ydd_Hebr',
                  'am': 'amh_Ethi', 'sn': 'sna_Latn', 'zu': 'zul_Latn', 'km': 'khm_Khmr', 'so': 'som_Latn', 'mi': 'mri_Latn',
                  'mt': 'mlt_Latn', 'lo': 'lao_Laoo', 'xh': 'xho_Latn', 'sm': 'smo_Latn', 'ny': 'nya_Latn', 'st': 'sot_Latn'}

    def __init__(self, device=-1):
        model = 'facebook/nllb-200-distilled-600M'
        print("Loading", model, "on device", device)
        self.translator = pipeline('translation',  model, device=device)

    def _l(self, lang):
        return self.FLORES_MAPPING[lang]

    def isLangSupported(self, lang):
        return lang in  self.FLORES_MAPPING

    def translate(self,tx, fromLang, toLang):        
        fromLang = self._l(fromLang)
        toLang = self._l(toLang)
        print("Translate from", fromLang, "to", toLang)
        output = self.translator(tx, src_lang=fromLang, tgt_lang=toLang)
        output = output[0]['translation_text']
        return output


def completePendingJob(rpcClient , translator):
    jobs=[]
    jobs.extend(rpcClient.getPendingJobs(rpc_pb2.RpcGetPendingJobs(filterByKind="5002")).jobs)
    jobs.extend(rpcClient.getPendingJobs(rpc_pb2.RpcGetPendingJobs(filterByRunOn="openagents\\/translate")).jobs)    
    if len(jobs)>0 : print(len(jobs),"pending jobs")

    for job in jobs:
        try:
            target_language = [x for x in job.param if x.key == "language" or x.key == "target_language"]
            target_language = "en" if len(target_language) == 0 else  target_language[0].value[0]

            source_language = [x for x in job.param if x.key == "source_language"]
            source_language = "en" if len(source_language) == 0 else source_language[0].value[0]

            print("Translating from", source_language, "to", target_language)
            if translator.isLangSupported(target_language) and translator.isLangSupported(source_language):
                rpcClient.acceptJob(rpc_pb2.RpcAcceptJob(jobId=job.id))
                rpcClient.logForJob(rpc_pb2.RpcJobLog(jobId=job.id, log="Translating from "+source_language+" to "+target_language))
                inputData = job.input[0].data
                outputData = translator.translate(content, source_language, target_language)
                rpcClient.completeJob(rpc_pb2.RpcJobOutput(jobId=job.id, output=outputData))
        except Exception as e:
            print("Error accepting job", job.id, e)
            rpcClient.cancelJob(rpc_pb2.RpcCancelJob(jobId=job.id, reason=str(e)))


def main():
    DEVICE = int(os.getenv('TRANSFORMERS_DEVICE', "-1"))
    NOSTR_CONNECT_GRPC_BINDING_ADDRESS = os.getenv('NOSTR_CONNECT_GRPC_BINDING_ADDRESS', "127.0.0.1")
    NOSTR_CONNECT_GRPC_BINDING_PORT = int(os.getenv('NOSTR_CONNECT_GRPC_BINDING_PORT', "5000"))
    t = Translator(DEVICE)
    while True:
        try:
            with grpc.insecure_channel(NOSTR_CONNECT_GRPC_BINDING_ADDRESS+":"+str(NOSTR_CONNECT_GRPC_BINDING_PORT)) as channel:
                print("Connected to "+NOSTR_CONNECT_GRPC_BINDING_ADDRESS+":"+str(NOSTR_CONNECT_GRPC_BINDING_PORT))
                stub = rpc_pb2_grpc.NostrConnectorStub(channel)
                while True:
                    completePendingJob(stub, t)
                    time.sleep(100.0/1000.0)
        except Exception as e:
            print("Error connecting to grpc server", e)
            
       

if __name__ == '__main__':
    main()