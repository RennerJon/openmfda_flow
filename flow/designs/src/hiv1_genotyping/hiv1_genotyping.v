module hiv1_genotyping (
	soln1,
	soln2,
	soln3,
	soln4,
	out 
);
input	soln1, soln2, soln3, soln4;
output	out;

wire	connect0,	connect1,	connect2,	connect3,	connect4,	connect5;

    
p_serpentine_0_240_30_8	serp0	(.in_fluid(soln1), .out_fluid(connect0));

p_serpentine_0_60_30_8	serp1	(.in_fluid(soln2), .out_fluid(connect1));

p_serpentine_0_60_30_8	serp2	(.in_fluid(soln3), .out_fluid(connect2));

p_serpentine_0_60_30_8	serp3	(.in_fluid(soln4), .out_fluid(connect3));
diffmix_25px_0	mix0	(.a_fluid(connect0), .b_fluid(connect1), .out_fluid(connect4));
diffmix_25px_0	mix1	(.a_fluid(connect2), .b_fluid(connect4), .out_fluid(connect5));
diffmix_25px_0	mix2	(.a_fluid(connect3), .b_fluid(connect5), .out_fluid(out));

    
endmodule
    