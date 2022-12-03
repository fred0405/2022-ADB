PROGRAM=${1:-python3 src/main.py}
shift
INDIR=${1:-./inputs}
shift
OUTDIR=${1:-./outputs}
echo "program=<$PROGRAM> indir=<$1> outdir=<$2>"

INS="`seq 1 23`"
INPRE="test"
OUTPRE="out"

for f in ${INS}; do
	echo "${PROGRAM} < ${INDIR}/${INPRE}${f} > ${OUTDIR}/${OUTPRE}${f}"
	${PROGRAM} < ${INDIR}/${INPRE}${f}.txt > ${OUTDIR}/${OUTPRE}${f}.txt_out &
done