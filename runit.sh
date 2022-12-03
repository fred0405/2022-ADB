PROGRAM=${1:-python3 src/main.py}
shift
INDIR=${1:-./inputs}
shift
OUTDIR=${1:-./outputs}
echo "program=<$PROGRAM> indir=<$INDIR> outdir=<$OUTDIR>"

INS="`seq 1 21`"
INPRE="test"
OUTPRE="out"

for f in ${INS}; do
	echo "${PROGRAM} < ${INDIR}/${INPRE}${f} > ${OUTDIR}/${OUTPRE}${f}"
	${PROGRAM} < ${INDIR}/${INPRE}${f} > ${OUTDIR}/${OUTPRE}${f}.txt_out &
done