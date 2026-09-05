import argparse
from backend.models.iceberg.random_forest_model import train_model

def main():
    parser=argparse.ArgumentParser(description='Antarctic maritime data and model commands')
    parser.add_argument('command',choices=['ingest','preprocess','train-iceberg','train-sea-ice','evaluate','predict','route'])
    args=parser.parse_args()
    if args.command == 'ingest': print('Ingestion adapters ready; demo mode uses bundled trajectory CSVs.')
    elif args.command == 'preprocess': print('Preprocessing contract: YYYYDDD UTC decoding, gap-aware sequences, and projected displacement.')
    elif args.command == 'train-iceberg': print(train_model())
    elif args.command == 'train-sea-ice': print('Sea-ice model not trained: Copernicus Marine sea-ice data is not configured.')
    elif args.command == 'evaluate': print('Model not evaluated: no trained model artifact exists.')
    elif args.command == 'predict': print('Use POST /api/predictions/iceberg for physics-baseline predictions.')
    else: print('Use POST /api/routes/optimize for A* route recommendations.')

if __name__ == '__main__': main()
